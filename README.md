# MasterChef

MasterChef es un plugin de Codex que entrega una receta completa en español, fiel a **una única fuente autorizada**. Conserva cantidades, raciones, tiempos y técnica publicados; si no puede leer la receta original, no la reconstruye de memoria.

## Qué puede hacer

1. **Receta concreta**: encuentra o parte de una receta solicitada.
2. **Despensa**: busca una receta compatible y señala los ingredientes que faltan.
3. **Antojo**: elige por sabor, textura, ocasión o apetencia.
4. **Descubrimiento contextual**: usa ciudad y país cuando hacen falta para clima, temporada o disponibilidad regional.

Ejemplos:

- «Usa $masterchef: quiero una tortilla de patatas con cebolla».
- «Tengo pasta, tomate y ajo. Busca algo y dime qué falta».
- «Solo puedo usar patata, huevos, sal y aceite».
- «Estoy en Valencia, España. Recomiéndame algo para hoy».

Las alergias, dieta, tiempo, equipo y «solo estos ingredientes» son límites duros. MasterChef no mezcla recetas ni inventa sustituciones, cantidades, tiempos o pasos; tampoco crea perfiles ni requiere cuentas personales. No formula diagnósticos ni atribuye efectos terapéuticos.

## Instalar en Codex

Necesitas Codex con soporte de plugins y marketplace sources. El identificador del plugin es `masterchef@masterchef` y la skill puede invocarse como `$masterchef`.

Cuando el repositorio sea público, registra el marketplace desde su slug de GitHub:

```bash
codex plugin marketplace add AdriAir/MasterChef-Skill --ref main
codex plugin add masterchef@masterchef
codex plugin list --json
```

También puedes usar la URL HTTPS:

```bash
codex plugin marketplace add https://github.com/AdriAir/MasterChef-Skill.git --ref main
```

El repositorio sigue siendo privado ahora. Una vez público, podrá instalarse sin credenciales Git; mientras sea privado requiere acceso. SSH es una alternativa opcional para quien ya use GitHub por SSH:

```bash
codex plugin marketplace add git@github.com:AdriAir/MasterChef-Skill.git --ref main
```

Para probar un checkout local, clónalo y añade el directorio actual:

```bash
git clone https://github.com/AdriAir/MasterChef-Skill.git MasterChef-Skill
cd MasterChef-Skill
codex plugin marketplace add .
codex plugin add masterchef@masterchef
```

## Fuentes y límites

El [registro cerrado de fuentes](skills/masterchef/references/sources.json) es la única autorización para recetas, tiempo, geocodificación, temporada y seguridad alimentaria. El helper offline requiere Python 3.9 o posterior y solo usa la biblioteca estándar:

```bash
python3 skills/masterchef/scripts/validate_sources.py validate
```

El helper valida URLs y propósitos; no sustituye la lectura de la ficha original. La cobertura meteorológica puede ser global, pero la temporada y disponibilidad dependen exactamente de las regiones indicadas en el registro. Si la localidad queda fuera de cobertura o no hay evidencia verificable, MasterChef lo indica. La búsqueda y lectura web las aporta el entorno donde se ejecuta Codex.

## Desarrollo y verificación

Los casos y resultados de verificación están en [docs/validation.md](docs/validation.md). La auditoría de publicación se documenta en [docs/publication-audit.md](docs/publication-audit.md).

Desde la raíz del checkout, el smoke test local usa un perfil temporal y no modifica tu instalación personal:

```bash
python3 scripts/smoke_plugin.py
```

Después de que el repositorio sea público, también se puede comprobar la instalación remota por HTTPS:

```bash
python3 scripts/smoke_plugin.py --source https://github.com/AdriAir/MasterChef-Skill.git
```

Usa `--source` con un origen de confianza: Codex instala el plugin indicado. La prueba comprueba que el helper instalado coincide con el de tu checkout y valida los datos con el helper local en modo Python aislado. Para una instalación reproducible, sustituye `--ref main` por el SHA completo de una revisión publicada y verificada.

## Licencia

El código y la documentación de este repositorio se distribuyen bajo la [licencia MIT](LICENSE). Las recetas, fotografías, marcas y contenidos de proveedores externos conservan sus propias licencias y condiciones de uso.
