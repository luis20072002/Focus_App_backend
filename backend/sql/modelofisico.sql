-- CREACIÓN DE LA BASE DE DATOS Y SU RESPECTIVO USO
CREATE DATABASE focus_app_bd;
USE focus_app_bd;

-- ROL

CREATE TABLE rol (
    id_rol INT,
    nombre_rol VARCHAR(30) NOT NULL,
    descripcion TEXT,

    CONSTRAINT rol_pk PRIMARY KEY (id_rol),
    CONSTRAINT rol_nombre_rol_un UNIQUE (nombre_rol)
);

-- USUARIO

CREATE TABLE usuario (
    id_usuario INT AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    nombre_usuario VARCHAR(30) NOT NULL,
    correo VARCHAR(100),
    telefono VARCHAR(20),
    contrasena_hash VARCHAR(255) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    foto_perfil VARCHAR(255),
    descripcion TEXT,
    perfil_privado BOOLEAN NOT NULL DEFAULT FALSE,
    foints_season INT NOT NULL DEFAULT 0,
    foints_totales INT NOT NULL DEFAULT 0,
    id_rol INT,
    fecha_registro DATETIME NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT usuario_pk PRIMARY KEY (id_usuario),
    CONSTRAINT usuario_nombre_usuario_un UNIQUE (nombre_usuario),
    CONSTRAINT usuario_correo_un UNIQUE (correo),
    CONSTRAINT usuario_telefono_un UNIQUE (telefono),

    CONSTRAINT usuario_id_rol_fk FOREIGN KEY (id_rol)
        REFERENCES rol(id_rol)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT usuario_contacto_ck CHECK (correo IS NOT NULL OR telefono IS NOT NULL),
    CONSTRAINT usuario_foints_totales_ck CHECK (foints_totales >= 0),
    CONSTRAINT usuario_foints_season_ck CHECK (foints_season >= 0)
);


-- CATEGORIA_PLANTILLA

CREATE TABLE categoria_plantilla (
    id_categoria INT AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,

    CONSTRAINT categoria_plantilla_pk PRIMARY KEY (id_categoria),
    CONSTRAINT categoria_plantilla_nombre_un UNIQUE (nombre)
);

-- TAREA_PLANTILLA

CREATE TABLE tarea_plantilla (
    id_tarea_plantilla INT AUTO_INCREMENT,
    id_categoria INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    foints_base INT NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT tarea_plantilla_pk PRIMARY KEY (id_tarea_plantilla),

    CONSTRAINT tarea_plantilla_id_categoria_fk FOREIGN KEY (id_categoria)
        REFERENCES categoria_plantilla(id_categoria)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT tarea_plantilla_foints_base_ck CHECK (foints_base > 0)
);

-- TAREA

CREATE TABLE tarea (
    id_tarea INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    id_tarea_plantilla INT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    es_urgente BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_programada DATETIME NOT NULL,
    tipo_notificacion ENUM('push','email','ninguna') NOT NULL,
    estado ENUM('pendiente','en_progreso','realizada','vencida') NOT NULL,
    foints_obtenidos INT,
    fecha_creacion DATETIME NOT NULL,

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

CREATE TABLE foto_confirmacion (
    id_foto INT AUTO_INCREMENT,
    id_tarea INT NOT NULL,
    id_usuario INT NOT NULL,
    url_foto VARCHAR(255) NOT NULL,
    visibilidad ENUM('global','amigos','seguidores') NOT NULL,
    fecha_subida DATETIME NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT foto_confirmacion_pk PRIMARY KEY (id_foto),

    CONSTRAINT foto_confirmacion_id_tarea_fk FOREIGN KEY (id_tarea)
        REFERENCES tarea(id_tarea)
        ON DELETE CASCADE,

    CONSTRAINT foto_confirmacion_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT foto_confirmacion_id_tarea_un UNIQUE (id_tarea)
);

-- LIKES

CREATE TABLE likes (
    id_like INT AUTO_INCREMENT,
    id_foto INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha DATETIME NOT NULL,

    CONSTRAINT likes_pk PRIMARY KEY (id_like),

    CONSTRAINT likes_id_foto_fk FOREIGN KEY (id_foto)
        REFERENCES foto_confirmacion(id_foto)
        ON DELETE CASCADE,

    CONSTRAINT likes_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT likes_id_foto_id_usuario_un UNIQUE (id_foto, id_usuario)
);

-- REPORTE

CREATE TABLE reporte (
    id_reporte INT AUTO_INCREMENT,
    id_foto INT NOT NULL,
    id_usuario INT NOT NULL,
    motivo TEXT NOT NULL,
    estado ENUM('pendiente','revisado','resuelto') NOT NULL DEFAULT 'pendiente',
    id_moderador INT,
    fecha_reporte DATETIME NOT NULL,
    fecha_revision DATETIME,

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
    id_seguimiento INT AUTO_INCREMENT,
    id_seguidor INT NOT NULL,
    id_seguido INT NOT NULL,
    fecha DATETIME NOT NULL,

    CONSTRAINT seguimiento_pk PRIMARY KEY (id_seguimiento),

    CONSTRAINT seguimiento_id_seguidor_fk FOREIGN KEY (id_seguidor)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT seguimiento_id_seguido_fk FOREIGN KEY (id_seguido)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT seguimiento_id_seguidor_id_seguido_un UNIQUE (id_seguidor, id_seguido),
    CONSTRAINT seguimiento_autoseguimiento_ck CHECK (id_seguidor <> id_seguido)
);

-- INSIGNIA

CREATE TABLE insignia (
    id_insignia INT AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,
    imagen_url VARCHAR(255),
    posicion_min INT NOT NULL,
    posicion_max INT NOT NULL,

    CONSTRAINT insignia_pk PRIMARY KEY (id_insignia),
    CONSTRAINT insignia_posicion_ck CHECK (posicion_min <= posicion_max)
);

-- USUARIO_INSIGNIA

CREATE TABLE usuario_insignia (
    id_usuario_insignia INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    id_insignia INT NOT NULL,
    ciclo_fecha_inicio DATE NOT NULL,
    ciclo_fecha_fin DATE NOT NULL,
    posicion_obtenida INT NOT NULL,

    CONSTRAINT usuario_insignia_pk PRIMARY KEY (id_usuario_insignia),

    CONSTRAINT usuario_insignia_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT usuario_insignia_id_insignia_fk FOREIGN KEY (id_insignia)
        REFERENCES insignia(id_insignia)
        ON DELETE CASCADE,

    CONSTRAINT usuario_insignia_ciclo_un UNIQUE (id_usuario, id_insignia, ciclo_fecha_inicio)
);


-- NOTIFICACION

CREATE TABLE notificacion (
    id_notificacion INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    tipo ENUM(
    'recordatorio_tarea',
    'tarea_vencida',
    'tarea_urgente',
    'nuevo_seguidor',
    'reporte_revisado',
    'foto_con_like',
    'sugerencia_resuelta') NOT NULL,
    mensaje TEXT NOT NULL,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    fecha DATETIME NOT NULL,
    id_referencia INT,

    CONSTRAINT notificacion_pk PRIMARY KEY (id_notificacion),

    CONSTRAINT notificacion_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);


-- SUGERENCIA_PLANTILLA

CREATE TABLE sugerencia_plantilla (
    id_sugerencia INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    tipo ENUM('tarea','categoria') NOT NULL,
    contenido TEXT NOT NULL,
    estado ENUM('pendiente','aprobada','rechazada') NOT NULL DEFAULT 'pendiente',
    id_admin INT,
    fecha DATETIME NOT NULL,

    CONSTRAINT sugerencia_plantilla_pk PRIMARY KEY (id_sugerencia),

    CONSTRAINT sugerencia_plantilla_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT sugerencia_plantilla_id_admin_fk FOREIGN KEY (id_admin)
        REFERENCES usuario(id_usuario)
        ON DELETE SET NULL
);


-- CONFIGURACION_USUARIO

CREATE TABLE configuracion_usuario (
    id_configuracion INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    notif_push BOOLEAN NOT NULL DEFAULT TRUE,
    notif_email BOOLEAN NOT NULL DEFAULT FALSE,
    notif_recordatorio_tarea    BOOLEAN NOT NULL DEFAULT TRUE,
	notif_tarea_vencida         BOOLEAN NOT NULL DEFAULT TRUE,
	notif_tarea_urgente         BOOLEAN NOT NULL DEFAULT TRUE,
	notif_nuevo_seguidor        BOOLEAN NOT NULL DEFAULT TRUE,
	notif_reporte_revisado      BOOLEAN NOT NULL DEFAULT TRUE,
	notif_foto_con_like         BOOLEAN NOT NULL DEFAULT TRUE,
	notif_sugerencia_resuelta   BOOLEAN NOT NULL DEFAULT TRUE,
    notif_recordatorio_min INT NOT NULL DEFAULT 30,
    tema ENUM('claro','oscuro') NOT NULL DEFAULT 'claro',
    idioma VARCHAR(10) NOT NULL DEFAULT 'es',
    para_que_usa_app TEXT,
    referido_por_amigo BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_actualizacion DATETIME NOT NULL,

    CONSTRAINT configuracion_usuario_pk PRIMARY KEY (id_configuracion),
    CONSTRAINT configuracion_usuario_id_usuario_un UNIQUE (id_usuario),

    CONSTRAINT configuracion_usuario_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);


-- TOKEN_VERIFICACION

CREATE TABLE token_verificacion (
    id_token INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    token VARCHAR(64) NOT NULL,
    tipo ENUM('recuperacion_contrasena','verificacion_cuenta') NOT NULL,
    medio_envio ENUM('correo','telefono') NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_expira DATETIME NOT NULL,
    fecha_creacion DATETIME NOT NULL,

    CONSTRAINT token_verificacion_pk PRIMARY KEY (id_token),
    CONSTRAINT token_verificacion_token_un UNIQUE (token),

    CONSTRAINT token_verificacion_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE
);

-- HISTORIAL_RANKING

CREATE TABLE historial_ranking (
    id_historial INT AUTO_INCREMENT,
    id_usuario INT NOT NULL,
    ciclo_fecha_inicio DATE NOT NULL,
    ciclo_fecha_fin DATE NOT NULL,
    posicion_global INT NOT NULL,
    foints_ciclo INT NOT NULL,

    CONSTRAINT historial_ranking_pk PRIMARY KEY (id_historial),

    CONSTRAINT historial_ranking_id_usuario_fk FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario)
        ON DELETE CASCADE,

    CONSTRAINT historial_ranking_posicion_ck CHECK (posicion_global > 0),
    CONSTRAINT historial_ranking_foints_ck CHECK (foints_ciclo >= 0),

    CONSTRAINT historial_ranking_ciclo_un UNIQUE (id_usuario, ciclo_fecha_inicio)
);