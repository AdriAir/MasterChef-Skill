# MasterChef

Skill de Codex que encuentra **una receta verificable, completa y en español**, fiel a una fuente autorizada. Puedes pedir un plato concreto, aprovechar tu despensa, describir un antojo o descubrir algo adecuado al tiempo y la temporada de tu localidad.

## Requisitos

- Codex con soporte de plugins y marketplace sources.
- Python 3.9 o posterior para el comprobador de fuentes, sin paquetes adicionales.
- Una herramienta de búsqueda y lectura web del entorno anfitrión que permita conocer la URL final. La skill no incorpora un navegador, MCP ni API de pago. Sin lectura de la receta original, no reconstruye recetas de memoria.
- Acceso Git al repositorio para instalarlo desde GitHub mientras sea privado. La conexión del plugin GitHub no configura por sí sola las credenciales del CLI Git.

## Instalar desde GitHub

Una vez publicados los archivos en el repositorio:

```bash
codex plugin marketplace add AdriAir/MasterChef-Skill --ref main
codex plugin add masterchef@masterchef
codex plugin list --json
```

Si tu acceso está configurado mediante SSH, puedes registrar la fuente así:

```bash
codex plugin marketplace add git@github.com:AdriAir/MasterChef-Skill.git --ref main
```

El identificador es `masterchef@masterchef` y la skill se invoca como `$masterchef`. También permite selección automática cuando la petición encaja. Si no aparece en una conversación ya abierta, vuelve a cargar las skills o abre una conversación nueva.

Para instalar un checkout local, usa su ruta absoluta en `codex plugin marketplace add` en lugar del repositorio GitHub.

## Ejemplos

- «Usa $masterchef: quiero una tortilla de patatas con cebolla».
- «Tengo pasta, tomate y ajo. Busca algo que pueda cocinar y dime qué me falta».
- «Solo puedo usar estos ingredientes: patata, huevos, sal y aceite».
- «Quiero algo crujiente y reconfortante, sin horno y en menos de 30 minutos».
- «Estoy en Valencia, España. Sorpréndeme con algo para hoy, según el tiempo y la temporada».

Recibirás el nombre, un motivo breve de elección, raciones, tiempos publicados, ingredientes, pasos y la atribución con enlace original. Los ingredientes faltantes se muestran cuando aportas una despensa. Se mantienen las raciones originales salvo que pidas otras.

No inventa sustituciones, cantidades, tiempos ni conversiones entre volumen y peso. «Solo estos» exige todos los ingredientes obligatorios; las opciones expresamente opcionales del autor pueden omitirse y se indica. Las restricciones de dieta, alergias, tiempo y equipo prevalecen sobre las preferencias. No garantiza ausencia de contaminación cruzada ni sustituye instrucciones sanitarias específicas.

## Fuentes y contexto

[sources.json](skills/masterchef/references/sources.json) es la única lista de autorización: contiene diez fuentes culinarias y fuentes separadas para tiempo, geocodificación, temporada y seguridad alimentaria. Cada entrada incluye hosts exactos, rutas permitidas, propósito, cobertura, criterio de atribución, justificación y enlaces de evidencia.

El tiempo tiene cobertura internacional; la temporada depende de la cobertura regional de las fuentes registradas. No se extrapola un calendario de Oregón a todo EE. UU., ni uno de Sídney a toda Australia. Una estación del año tampoco prueba que un producto sea local o esté disponible. Si falta información verificable se declara el límite.

La skill pide ciudad y país solo cuando son necesarios. No crea perfiles ni historiales propios; minimiza la ubicación transmitida a servicios y filtra las alergias localmente. Las herramientas y proveedores pueden aplicar sus propias políticas de registro.

El validador es **offline**: comprueba la autorización de las URLs conocidas, no el contenido editorial, la vigencia de datos, la cobertura de una ciudad ni el tráfico interno de una herramienta. La skill aplica esas comprobaciones adicionales. Este paquete no constituye un sandbox de red.

## Comprobar o mantener el registro

Desde la raíz del checkout:

```bash
python3 skills/masterchef/scripts/validate_sources.py validate
python3 skills/masterchef/scripts/validate_sources.py check 'https://www.kingarthurbaking.com/recipes/classic-sandwich-bread-recipe' --purpose recipe
```

Para comprobar una redirección conocida, añade `--final-url 'URL_FINAL'`. Solo se acepta un destino incluido en la misma entrada de fuente y con el mismo propósito. `--registry PATH` permite comprobar otra copia del registro. Las rutas por defecto se resuelven desde el script, independientemente del directorio de trabajo.

El resultado es JSON: éxito `0`, rechazo o registro inválido `1`, argumentos incorrectos `2`. `check` devuelve `allowed`, `reason` y, si permite, `source_id`; `validate` devuelve `valid` y `errors`.

Para modificar fuentes, edita únicamente el registro y revisa la autoría, la evidencia editorial, los hosts y las rutas reales. Usa `paths` para rutas exactas y `path_prefixes` terminados en `/` para secciones; no se admiten comodines. Un prefijo `/` solo corresponde a sitios que publican las recetas como slugs en la raíz y no elimina la comprobación editorial. `checked_at` registra la revisión de la entrada, no garantiza disponibilidad futura. Una fuente enlazada por otra no queda autorizada automáticamente.

## Desarrollo y verificación

```bash
python3 -m unittest discover -s tests -v
python3 skills/masterchef/scripts/validate_sources.py validate
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate_package.py
python3 scripts/smoke_plugin.py
```

PyYAML se usa únicamente en la validación de desarrollo de los manifiestos YAML. El helper de la skill y sus pruebas de URL funcionan con la biblioteca estándar.

El smoke test crea un `CODEX_HOME` temporal solo para sus procesos hijos: registra el marketplace local, instala el plugin, comprueba que queda habilitado y ejecuta el helper de la copia instalada desde otro directorio. No modifica la instalación personal ni demuestra acceso Git remoto o calidad de las recetas; esos aspectos se verifican por separado.

Los casos conductuales y el estado de verificación están en [docs/validation.md](docs/validation.md).
