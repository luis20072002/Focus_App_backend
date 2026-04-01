-- Database: focus_app_bd

-- DROP DATABASE IF EXISTS focus_app_bd;

CREATE DATABASE focus_app_bd
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Colombia.1252'
    LC_CTYPE = 'Spanish_Colombia.1252'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

-- ROL

CREATE TABLE rol (
    id_rol       INT,
    nombre_rol   VARCHAR(30)  NOT NULL,
    descripcion  TEXT,

    CONSTRAINT rol_pk            PRIMARY KEY (id_rol),
    CONSTRAINT rol_nombre_rol_un UNIQUE (nombre_rol)
);

-- USUARIO

CREATE TABLE usuario (
    id_usuario       SERIAL,
    nombre           VARCHAR(50)  NOT NULL,
    apellido         VARCHAR(50)  NOT NULL,
    nombre_usuario   VARCHAR(30)  NOT NULL,
    correo           VARCHAR(100),
    telefono         VARCHAR(20),
    contrasena_hash  VARCHAR(255) NOT NULL,
    fecha_nacimiento DATE         NOT NULL,
    foto_perfil      VARCHAR(255),
    descripcion      TEXT,
    perfil_privado   BOOLEAN      NOT NULL DEFAULT FALSE,
    foints_season    INT          NOT NULL DEFAULT 0,
    foints_totales   INT          NOT NULL DEFAULT 0,
    id_rol           INT,
    fecha_registro   TIMESTAMP    NOT NULL,
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,

    CONSTRAINT usuario_pk              PRIMARY KEY (id_usuario),
    CONSTRAINT usuario_nombre_usuario_un UNIQUE (nombre_usuario),
    CONSTRAINT usuario_correo_un       UNIQUE (correo),
    CONSTRAINT usuario_telefono_un     UNIQUE (telefono),

    CONSTRAINT usuario_id_rol_fk FOREIGN KEY (id_rol)
        REFERENCES rol(id_rol)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT usuario_contacto_ck      CHECK (correo IS NOT NULL OR telefono IS NOT NULL),
    CONSTRAINT usuario_foints_totales_ck CHECK (foints_totales >= 0),
    CONSTRAINT usuario_foints_season_ck  CHECK (foints_season >= 0)
);

-- CATEGORIA_PLANTILLA

CREATE TABLE categoria_plantilla (
    id_categoria  SERIAL,
    nombre        VARCHAR(50) NOT NULL,
    descripcion   TEXT,

    CONSTRAINT categoria_plantilla_pk       PRIMARY KEY (id_categoria),
    CONSTRAINT categoria_plantilla_nombre_un UNIQUE (nombre)
);

-- TAREA_PLANTILLA

CREATE TABLE tarea_plantilla (
    id_tarea_plantilla  SERIAL,
    id_categoria        INT          NOT NULL,
    nombre              VARCHAR(100) NOT NULL,
    descripcion         TEXT,
    foints_base         INT          NOT NULL,
    activa              BOOLEAN      NOT NULL DEFAULT TRUE,

    CONSTRAINT tarea_plantilla_pk PRIMARY KEY (id_tarea_plantilla),

    CONSTRAINT tarea_plantilla_id_categoria_fk FOREIGN KEY (id_categoria)
        REFERENCES categoria_plantilla(id_categoria)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT tarea_plantilla_foints_base_ck CHECK (foints_base > 0)
);

-- TAREA
-- Nota: ENUM de MySQL se reemplaza con tipos TEXT + CHECK en PostgreSQL.
-- Alternativa: CREATE TYPE ... AS ENUM (...) antes de crear la tabla.

CREATE TYPE tarea_tipo_notificacion AS ENUM ('push', 'email', 'ninguna');
CREATE TYPE tarea_estado_enum       AS ENUM ('pendiente', 'en_progreso', 'realizada', 'vencida');

CREATE TABLE tarea (
    id_tarea           SERIAL,
    id_usuario         INT                        NOT NULL,
    id_tarea_plantilla INT,
    nombre             VARCHAR(100)               NOT NULL,
    descripcion        TEXT,
    es_urgente         BOOLEAN                    NOT NULL DEFAULT FALSE,
    fecha_programada   TIMESTAMP                  NOT NULL,
    tipo_notificacion  tarea_tipo_notificacion    NOT NULL,
    estado             tarea_estado_enum          NOT NULL,
    foints_obtenidos   INT,
    fecha_creacion     TIMESTAMP                  NOT NULL,

    CONSTRAINT tarea_pk PRIMARY KEY (id_tarea),

    CONSTRAINT tarea_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT tarea_id_tarea_plantilla_fk FOREIGN KEY (id_tarea_plantilla)
        REFERENCES tarea_plantilla(id_tarea_plantilla)
        ON DELETE SET NULL,

    CONSTRAINT tarea_foints_obtenidos_ck CHECK (foints_obtenidos IS NULL OR foints_obtenidos >= 0)
);

-- FOTO_CONFIRMACION

CREATE TYPE foto_visibilidad_enum AS ENUM ('global', 'amigos', 'seguidores');

CREATE TABLE foto_confirmacion (
    id_foto      SERIAL,
    id_tarea     INT                    NOT NULL,
    id_usuario   INT                    NOT NULL,
    url_foto     VARCHAR(255)           NOT NULL,
    visibilidad  foto_visibilidad_enum  NOT NULL,
    fecha_subida TIMESTAMP              NOT NULL,
    activa       BOOLEAN                NOT NULL DEFAULT TRUE,

    CONSTRAINT foto_confirmacion_pk         PRIMARY KEY (id_foto),
    CONSTRAINT foto_confirmacion_id_tarea_un UNIQUE (id_tarea),

    CONSTRAINT foto_confirmacion_id_tarea_fk FOREIGN KEY (id_tarea)
        REFERENCES tarea(id_tarea)
        ON DELETE CASCADE,

    CONSTRAINT foto_confirmacion_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- LIKES

CREATE TABLE likes (
    id_like    SERIAL,
    id_foto    INT       NOT NULL,
    id_usuario INT       NOT NULL,
    fecha      TIMESTAMP NOT NULL,

    CONSTRAINT likes_pk                    PRIMARY KEY (id_like),
    CONSTRAINT likes_id_foto_id_usuario_un UNIQUE (id_foto, id_usuario),

    CONSTRAINT likes_id_foto_fk FOREIGN KEY (id_foto)
        REFERENCES foto_confirmacion(id_foto)
        ON DELETE CASCADE,

    CONSTRAINT likes_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- REPORTE

CREATE TYPE reporte_estado_enum AS ENUM ('pendiente', 'revisado', 'resuelto');

CREATE TABLE reporte (
    id_reporte      SERIAL,
    id_foto         INT                  NOT NULL,
    id_usuario      INT                  NOT NULL,
    motivo          TEXT                 NOT NULL,
    estado          reporte_estado_enum  NOT NULL DEFAULT 'pendiente',
    id_moderador    INT,
    fecha_reporte   TIMESTAMP            NOT NULL,
    fecha_revision  TIMESTAMP,

    CONSTRAINT reporte_pk PRIMARY KEY (id_reporte),

    CONSTRAINT reporte_id_foto_fk FOREIGN KEY (id_foto)
        REFERENCES foto_confirmacion(id_foto)
        ON DELETE CASCADE,

    CONSTRAINT reporte_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT reporte_id_moderador_fk FOREIGN KEY (id_moderador)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL
);

-- SEGUIMIENTO

CREATE TABLE seguimiento (
    id_seguimiento  SERIAL,
    id_seguidor     INT       NOT NULL,
    id_seguido      INT       NOT NULL,
    fecha           TIMESTAMP NOT NULL,

    CONSTRAINT seguimiento_pk                        PRIMARY KEY (id_seguimiento),
    CONSTRAINT seguimiento_id_seguidor_id_seguido_un UNIQUE (id_seguidor, id_seguido),
    CONSTRAINT seguimiento_autoseguimiento_ck        CHECK (id_seguidor <> id_seguido),

    CONSTRAINT seguimiento_id_seguidor_fk FOREIGN KEY (id_seguidor)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT seguimiento_id_seguido_fk FOREIGN KEY (id_seguido)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- INSIGNIA

CREATE TABLE insignia (
    id_insignia   SERIAL,
    nombre        VARCHAR(50) NOT NULL,
    descripcion   TEXT,
    imagen_url    VARCHAR(255),
    posicion_min  INT         NOT NULL,
    posicion_max  INT         NOT NULL,

    CONSTRAINT insignia_pk        PRIMARY KEY (id_insignia),
    CONSTRAINT insignia_posicion_ck CHECK (posicion_min <= posicion_max)
);

-- USUARIO_INSIGNIA

CREATE TABLE usuario_insignia (
    id_usuario_insignia  SERIAL,
    id_usuario           INT  NOT NULL,
    id_insignia          INT  NOT NULL,
    ciclo_fecha_inicio   DATE NOT NULL,
    ciclo_fecha_fin      DATE NOT NULL,
    posicion_obtenida    INT  NOT NULL,

    CONSTRAINT usuario_insignia_pk       PRIMARY KEY (id_usuario_insignia),
    CONSTRAINT usuario_insignia_ciclo_un UNIQUE (id_usuario, id_insignia, ciclo_fecha_inicio),

    CONSTRAINT usuario_insignia_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT usuario_insignia_id_insignia_fk FOREIGN KEY (id_insignia)
        REFERENCES insignia(id_insignia)
        ON DELETE CASCADE
);

-- NOTIFICACION

CREATE TYPE notificacion_tipo_enum AS ENUM (
    'recordatorio_tarea',
    'tarea_vencida',
    'tarea_urgente',
    'nuevo_seguidor',
    'reporte_revisado',
    'foto_con_like',
    'sugerencia_resuelta'
);

CREATE TABLE notificacion (
    id_notificacion  SERIAL,
    id_usuario       INT                    NOT NULL,
    tipo             notificacion_tipo_enum NOT NULL,
    mensaje          TEXT                   NOT NULL,
    leida            BOOLEAN                NOT NULL DEFAULT FALSE,
    fecha            TIMESTAMP              NOT NULL,
    id_referencia    INT,

    CONSTRAINT notificacion_pk PRIMARY KEY (id_notificacion),

    CONSTRAINT notificacion_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- SUGERENCIA_PLANTILLA

CREATE TYPE sugerencia_tipo_enum   AS ENUM ('tarea', 'categoria');
CREATE TYPE sugerencia_estado_enum AS ENUM ('pendiente', 'aprobada', 'rechazada');

CREATE TABLE sugerencia_plantilla (
    id_sugerencia  SERIAL,
    id_usuario     INT                    NOT NULL,
    tipo           sugerencia_tipo_enum   NOT NULL,
    contenido      TEXT                   NOT NULL,
    estado         sugerencia_estado_enum NOT NULL DEFAULT 'pendiente',
    id_admin       INT,
    fecha          TIMESTAMP              NOT NULL,

    CONSTRAINT sugerencia_plantilla_pk PRIMARY KEY (id_sugerencia),

    CONSTRAINT sugerencia_plantilla_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT sugerencia_plantilla_id_admin_fk FOREIGN KEY (id_admin)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL
);

-- CONFIGURACION_USUARIO

CREATE TYPE tema_enum AS ENUM ('claro', 'oscuro');

CREATE TABLE configuracion_usuario (
    id_configuracion             SERIAL,
    id_usuario                   INT          NOT NULL,
    notif_push                   BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_email                  BOOLEAN      NOT NULL DEFAULT FALSE,
    notif_recordatorio_tarea     BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_tarea_vencida          BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_tarea_urgente          BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_nuevo_seguidor         BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_reporte_revisado       BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_foto_con_like          BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_sugerencia_resuelta    BOOLEAN      NOT NULL DEFAULT TRUE,
    notif_recordatorio_min       INT          NOT NULL DEFAULT 30,
    tema                         tema_enum    NOT NULL DEFAULT 'claro',
    idioma                       VARCHAR(10)  NOT NULL DEFAULT 'es',
    para_que_usa_app             TEXT,
    referido_por_amigo           BOOLEAN      NOT NULL DEFAULT FALSE,
    fecha_actualizacion          TIMESTAMP    NOT NULL,

    CONSTRAINT configuracion_usuario_pk          PRIMARY KEY (id_configuracion),
    CONSTRAINT configuracion_usuario_id_usuario_un UNIQUE (id_usuario),

    CONSTRAINT configuracion_usuario_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- TOKEN_VERIFICACION

CREATE TYPE token_tipo_enum       AS ENUM ('recuperacion_contrasena', 'verificacion_cuenta');
CREATE TYPE token_medio_envio_enum AS ENUM ('correo', 'telefono');

CREATE TABLE token_verificacion (
    id_token        SERIAL,
    id_usuario      INT                    NOT NULL,
    token           VARCHAR(64)            NOT NULL,
    tipo            token_tipo_enum        NOT NULL,
    medio_envio     token_medio_envio_enum NOT NULL,
    usado           BOOLEAN                NOT NULL DEFAULT FALSE,
    fecha_expira    TIMESTAMP              NOT NULL,
    fecha_creacion  TIMESTAMP              NOT NULL,

    CONSTRAINT token_verificacion_pk       PRIMARY KEY (id_token),
    CONSTRAINT token_verificacion_token_un UNIQUE (token),

    CONSTRAINT token_verificacion_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- HISTORIAL_RANKING

CREATE TABLE historial_ranking (
    id_historial        SERIAL,
    id_usuario          INT  NOT NULL,
    ciclo_fecha_inicio  DATE NOT NULL,
    ciclo_fecha_fin     DATE NOT NULL,
    posicion_global     INT  NOT NULL,
    foints_ciclo        INT  NOT NULL,

    CONSTRAINT historial_ranking_pk        PRIMARY KEY (id_historial),
    CONSTRAINT historial_ranking_ciclo_un  UNIQUE (id_usuario, ciclo_fecha_inicio),
    CONSTRAINT historial_ranking_posicion_ck CHECK (posicion_global > 0),
    CONSTRAINT historial_ranking_foints_ck   CHECK (foints_ciclo >= 0),

    CONSTRAINT historial_ranking_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);