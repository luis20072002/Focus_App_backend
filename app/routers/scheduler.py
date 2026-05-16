"""
scheduler.py — Jobs periódicos con APScheduler

Instalación:
    pip install apscheduler

Jobs registrados:
  1. job_recordatorio_tareas     — cada minuto
       Detecta tareas con scheduled_date entre ahora y ahora+reminder_minutes
       y envía push si aún no se mandó recordatorio (notification_type=push).

  2. job_tareas_vencidas         — cada 5 minutos
       Detecta tareas pending/in_progress cuya scheduled_date ya pasó,
       las marca como expired y envía push de aviso.

  3. job_cierre_automatico_ciclo — cada hora
       Si hay un ciclo activo cuya end_date ya pasó, lo cierra automáticamente
       llamando a la misma lógica de POST /ranking/cycles/close.

Integración con FastAPI:
    El scheduler arranca en el evento startup de la app y se detiene en shutdown.
    Ver main.py para el registro de los eventos.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.task import Task, TaskStatus, TaskNotificationType
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.notification import Notification, NotificationType
from app.models.ranking_cycle import RankingCycle
from app.models.ranking_history import RankingHistory
from app.models.badge import Badge
from app.models.user_badge import UserBadge
from app.routers.notificationsRT import enviar_push_a_usuario, crear_notificacion_db

scheduler = AsyncIOScheduler(timezone="UTC")


# ---------------------------------------------------------------------------
# Utilidad: obtener sesión de BD fuera del ciclo de request
# ---------------------------------------------------------------------------

def get_db_session() -> Session:
    """Crea una sesión de BD independiente para uso en jobs."""
    return SessionLocal()


# ---------------------------------------------------------------------------
# Utilidad compartida con rankingRT: otorgar badges al cerrar ciclo
# ---------------------------------------------------------------------------

def _otorgar_badges(usuarios_ordenados: list[User], ciclo: RankingCycle, db: Session) -> int:
    """
    Replica la lógica de otorgar_badges de rankingRT para uso interno
    del scheduler sin crear dependencia circular entre módulos.
    """
    badges = db.query(Badge).all()
    if not badges:
        return 0

    cycle_start = ciclo.start_date.date()
    cycle_end = ciclo.end_date.date()
    badges_otorgados = 0

    for posicion, usuario in enumerate(usuarios_ordenados, start=1):
        badge_aplicable = next(
            (b for b in badges if b.min_position <= posicion <= b.max_position),
            None,
        )
        if badge_aplicable is None:
            break

        ya_tiene = db.query(UserBadge).filter(
            UserBadge.id_user == usuario.id_user,
            UserBadge.id_badge == badge_aplicable.id_badge,
            UserBadge.cycle_start_date == cycle_start,
        ).first()

        if ya_tiene:
            continue

        db.add(UserBadge(
            id_user=usuario.id_user,
            id_badge=badge_aplicable.id_badge,
            cycle_start_date=cycle_start,
            cycle_end_date=cycle_end,
            position_obtained=posicion,
        ))
        badges_otorgados += 1

    return badges_otorgados


# ===========================================================================
# JOB 1 — Recordatorios de tareas próximas (cada 1 minuto)
# ===========================================================================

def job_recordatorio_tareas() -> None:
    """
    Detecta tareas que deben recibir recordatorio push y las notifica.

    Lógica:
    - Para cada usuario con notif_push=True y notif_task_reminder=True,
      obtiene su notif_reminder_minutes (default 30).
    - Busca tareas pending con notification_type=push cuyo scheduled_date
      esté dentro de la ventana [ahora, ahora + reminder_minutes].
    - Verifica que NO exista ya una Notification de tipo task_reminder
      para esa tarea (evita enviar duplicados en cada ejecución del job).
    - Crea la Notification en BD y envía push.

    El job corre cada minuto — la ventana de detección garantiza que
    una tarea con reminder_minutes=30 sea detectada en alguna de las
    30 ejecuciones previas a su hora, pero solo notificada una vez
    gracias a la verificación de duplicados.
    """
    db = get_db_session()
    try:
        ahora = datetime.utcnow()

        # Obtener configuraciones con recordatorio activo
        configs = db.query(UserSettings).filter(
            UserSettings.notif_push == True,
            UserSettings.notif_task_reminder == True,
        ).all()

        for config in configs:
            ventana_fin = ahora + timedelta(minutes=config.notif_reminder_minutes)

            # Tareas pendientes del usuario en la ventana de recordatorio
            tareas = db.query(Task).filter(
                Task.id_user == config.id_user,
                Task.status == TaskStatus.pending,
                Task.notification_type == TaskNotificationType.push,
                Task.scheduled_date >= ahora,
                Task.scheduled_date <= ventana_fin,
            ).all()

            for tarea in tareas:
                # Verificar que no se haya enviado ya el recordatorio para esta tarea
                ya_notificado = db.query(Notification).filter(
                    Notification.id_user == config.id_user,
                    Notification.type == NotificationType.task_reminder,
                    Notification.id_reference == tarea.id_task,
                ).first()

                if ya_notificado:
                    continue

                minutos_restantes = int(
                    (tarea.scheduled_date - ahora).total_seconds() / 60
                )
                mensaje = (
                    f"Tienes '{tarea.name}' programada "
                    f"en {minutos_restantes} minuto{'s' if minutos_restantes != 1 else ''}."
                )

                crear_notificacion_db(
                    id_user=config.id_user,
                    tipo=NotificationType.task_reminder,
                    mensaje=mensaje,
                    db=db,
                    id_reference=tarea.id_task,
                )
                enviar_push_a_usuario(
                    id_user=config.id_user,
                    titulo="Recordatorio de tarea",
                    cuerpo=mensaje,
                    db=db,
                )

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[scheduler] Error en job_recordatorio_tareas: {e}")
    finally:
        db.close()


# ===========================================================================
# JOB 2 — Marcar tareas vencidas y notificar (cada 5 minutos)
# ===========================================================================

def job_tareas_vencidas() -> None:
    """
    Detecta tareas pending/in_progress cuya scheduled_date ya pasó,
    las marca como expired y envía notificación push si el usuario
    tiene notif_task_expired=True.

    Se ejecuta cada 5 minutos — una tarea puede quedar marcada como
    vencida con hasta 5 minutos de retraso respecto a su scheduled_date,
    lo cual es aceptable para el caso de uso.

    Las tareas recurrentes virtuales no tienen fila propia en BD,
    por lo que este job solo afecta tareas no recurrentes (is_recurrent=False).
    Para recurrentes, el cliente calcula el estado en el calendario.
    """
    db = get_db_session()
    try:
        ahora = datetime.utcnow()

        tareas_vencidas = db.query(Task).filter(
            Task.status.in_([TaskStatus.pending, TaskStatus.in_progress]),
            Task.is_recurrent == False,
            Task.scheduled_date < ahora,
        ).all()

        if not tareas_vencidas:
            return

        # Cargar configuraciones de usuarios afectados en un solo query
        ids_usuarios = list({t.id_user for t in tareas_vencidas})
        configs = {
            c.id_user: c
            for c in db.query(UserSettings).filter(
                UserSettings.id_user.in_(ids_usuarios),
            ).all()
        }

        for tarea in tareas_vencidas:
            tarea.status = TaskStatus.expired
            config = configs.get(tarea.id_user)

            # Notificar solo si el usuario tiene push y aviso de vencidas activos
            if not config or not config.notif_push or not config.notif_task_expired:
                continue

            # Verificar que no se haya notificado ya el vencimiento
            ya_notificado = db.query(Notification).filter(
                Notification.id_user == tarea.id_user,
                Notification.type == NotificationType.task_expired,
                Notification.id_reference == tarea.id_task,
            ).first()

            if ya_notificado:
                continue

            mensaje = f"La tarea '{tarea.name}' venció sin ser completada."

            crear_notificacion_db(
                id_user=tarea.id_user,
                tipo=NotificationType.task_expired,
                mensaje=mensaje,
                db=db,
                id_reference=tarea.id_task,
            )
            enviar_push_a_usuario(
                id_user=tarea.id_user,
                titulo="Tarea vencida",
                cuerpo=mensaje,
                db=db,
            )

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"[scheduler] Error en job_tareas_vencidas: {e}")
    finally:
        db.close()


# ===========================================================================
# JOB 3 — Cierre automático de ciclo de ranking (cada hora)
# ===========================================================================

def job_cierre_automatico_ciclo() -> None:
    """
    Si hay un ciclo de ranking activo cuya end_date ya pasó,
    lo cierra automáticamente ejecutando el mismo flujo que
    POST /ranking/cycles/close:

      1. Obtiene ranking final (usuarios activos con foints_season > 0).
      2. Guarda snapshot en RankingHistory.
      3. Otorga badges según posición.
      4. Resetea foints_season a 0 en todos los usuarios activos.
      5. Marca el ciclo como closed=True con closed_at=ahora.

    El job corre cada hora — el ciclo puede cerrarse con hasta 1 hora
    de retraso respecto a su end_date, lo cual es aceptable dado que
    los ciclos duran ~15 días.

    Si no hay ciclo activo o su end_date aún no llegó, el job no hace nada.
    """
    db = get_db_session()
    try:
        ahora = datetime.utcnow()

        ciclo = db.query(RankingCycle).filter(
            RankingCycle.closed == False,
        ).first()

        if not ciclo:
            return  # No hay ciclo activo

        if ciclo.end_date > ahora:
            return  # El ciclo aún no terminó

        print(f"[scheduler] Cerrando ciclo {ciclo.id_cycle} automáticamente...")

        # 1. Ranking final
        usuarios_rankeados = (
            db.query(User)
            .filter(User.active == True, User.foints_season > 0)
            .order_by(User.foints_season.desc(), User.username.asc())
            .all()
        )

        # 2. Snapshot en RankingHistory
        for posicion, usuario in enumerate(usuarios_rankeados, start=1):
            db.add(RankingHistory(
                id_user=usuario.id_user,
                global_position=posicion,
                foints_cycle=usuario.foints_season,
                id_cycle=ciclo.id_cycle,
            ))

        db.flush()

        # 3. Otorgar badges
        badges_otorgados = _otorgar_badges(usuarios_rankeados, ciclo, db)

        # 4. Resetear foints_season
        db.query(User).filter(User.active == True).update({"foints_season": 0})

        # 5. Cerrar ciclo
        ciclo.closed = True
        ciclo.closed_at = ahora

        db.commit()
        print(
            f"[scheduler] Ciclo {ciclo.id_cycle} cerrado. "
            f"Usuarios rankeados: {len(usuarios_rankeados)}, "
            f"Badges otorgados: {badges_otorgados}."
        )

    except Exception as e:
        db.rollback()
        print(f"[scheduler] Error en job_cierre_automatico_ciclo: {e}")
    finally:
        db.close()


# ===========================================================================
# Registro de jobs
# ===========================================================================

def registrar_jobs() -> None:
    """
    Registra todos los jobs en el scheduler.
    Llamar una sola vez desde el evento startup de FastAPI.
    """
    scheduler.add_job(
        job_recordatorio_tareas,
        trigger=IntervalTrigger(minutes=1),
        id="recordatorio_tareas",
        name="Recordatorios de tareas próximas",
        replace_existing=True,
        misfire_grace_time=30,       # Si el job se retrasa ≤30s, igual corre
    )

    scheduler.add_job(
        job_tareas_vencidas,
        trigger=IntervalTrigger(minutes=5),
        id="tareas_vencidas",
        name="Marcar tareas vencidas",
        replace_existing=True,
        misfire_grace_time=60,
    )

    scheduler.add_job(
        job_cierre_automatico_ciclo,
        trigger=IntervalTrigger(hours=1),
        id="cierre_ciclo",
        name="Cierre automático de ciclo de ranking",
        replace_existing=True,
        misfire_grace_time=300,      # 5 min de gracia — si el servidor estuvo caído
    )