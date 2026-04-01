# Focus App

Focus App es una aplicación móvil orientada a mejorar la productividad personal mediante la organización de tareas, el uso de mecánicas de gamificación y la interacción social entre usuarios.

## Equipo de desarrollo

El proyecto es desarrollado por Luis Mendoza, Santiago Cuesta, Dayana Narváez y Daniela Arrieta.

## ¿Qué es Focus App?

Focus App surge como una respuesta al problema común de la procrastinación y la falta de organización en la vida diaria, especialmente en estudiantes y jóvenes. La aplicación no se limita a funcionar como una agenda tradicional, sino que propone una experiencia más dinámica en la que el cumplimiento de tareas se convierte en una actividad motivada por recompensas y reconocimiento social.

El sistema integra un modelo de seguimiento de actividades diarias con un enfoque interactivo, en el que los usuarios pueden visualizar sus tareas, organizarlas en el tiempo y recibir recordatorios que facilitan su cumplimiento. A esto se suma un componente social que permite observar el progreso de otros usuarios y compararlo mediante un sistema de puntuación.

## Objetivo del proyecto

El propósito principal de Focus App es proporcionar una herramienta que permita a los usuarios gestionar su tiempo de manera más eficiente, promoviendo la creación de hábitos positivos y reduciendo la tendencia a postergar actividades importantes. A través de la combinación de organización personal y elementos de motivación externa, la aplicación busca generar constancia en el cumplimiento de tareas.

## Funcionamiento general

El usuario puede registrarse en la plataforma proporcionando sus datos básicos y, una vez dentro del sistema, tiene acceso a una serie de pantallas principales que estructuran la experiencia de uso. En la pantalla de inicio se presentan las tareas pendientes del día junto con un sistema de ranking que refleja el desempeño del usuario frente a otros.

El sistema permite crear tareas personalizadas o seleccionar tareas a partir de una plantilla predefinida. Estas últimas son las únicas que pueden otorgar puntos, denominados “Foints”, siempre que el usuario decida marcarlas como candidatas para obtenerlos. En estos casos, la aplicación solicita una confirmación mediante evidencia, generalmente una fotografía tomada desde la misma app, lo que valida la realización de la actividad.

Además, la aplicación incorpora un sistema de notificaciones que recuerda al usuario sus tareas programadas, así como eventos relevantes relacionados con su actividad o interacción con otros usuarios. También incluye un módulo social donde se pueden visualizar publicaciones, interactuar mediante “me gusta” y seguir a otros usuarios, generando una red de seguimiento mutuo.

## Sistema de puntuación

El sistema de Foints constituye uno de los elementos centrales de la aplicación. Estos puntos se otorgan al completar tareas provenientes de la plantilla, y su valor puede variar dependiendo del cumplimiento en el tiempo establecido. Si una tarea no se completa dentro del plazo definido, la cantidad de puntos otorgados disminuye progresivamente.

Los puntos acumulados permiten posicionar al usuario dentro de un ranking global y entre sus contactos. Este ranking se reinicia periódicamente, lo que introduce una dinámica competitiva constante y brinda oportunidades recurrentes para destacar.

## Arquitectura del proyecto

El proyecto se encuentra dividido en dos componentes principales. Por un lado, un frontend desarrollado en Flutter, encargado de la interfaz de usuario y la experiencia visual. Por otro lado, un backend que gestiona la lógica del sistema, incluyendo autenticación, manejo de tareas, cálculo de puntos, notificaciones y persistencia de datos.

La base de datos está estructurada para soportar entidades como usuarios, tareas, fotografías de confirmación, interacciones sociales, notificaciones y rankings, permitiendo una gestión coherente de la información dentro del sistema.

## Estado del proyecto

Actualmente, el proyecto se encuentra en fase de desarrollo, con una estructura base funcional que incluye la definición de requisitos, el diseño de la base de datos y una implementación inicial tanto del frontend como del backend.

## Consideraciones finales

Focus App plantea una alternativa a las herramientas tradicionales de organización, integrando elementos de motivación y competencia que buscan influir positivamente en el comportamiento del usuario. El enfoque del proyecto no solo está en la gestión de tareas, sino en la forma en que estas se convierten en parte de una dinámica constante de mejora personal.
