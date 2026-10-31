# Diagnósticos reales del entorno

- El checkout inicial no contenía commits ni archivos. `git ls-remote origin`
  accedió al repositorio remoto y no obtuvo referencias; no existía `main`.
- El sandbox local no podía abrir el proxy; las operaciones de red se ejecutaron
  con la escalación de sandbox soportada, manteniendo proxy y TLS verificado.
- Se extrajeron las URLs del PDF con pypdf. El primer sondeo de un mirror distinto
  respondió 404 y no se utilizó. Los dos enlaces del PDF descargaron CSV cuyas
  huellas coincidieron exactamente con el anexo.
- DVC intentó escribir en `/var/tmp/dvc` (sólo lectura). Se utilizó el ajuste
  soportado `DVC_SITE_CACHE_DIR` dentro de una ruta local escribible. No se
  modificó DVC ni se desactivó verificación de integridad.
- DVC 3.63.0 falló al importar `_DIR_MARK` con pathspec 1.1.1. Se fijó
  `pathspec==0.12.1`, se instaló y se probó con un DVC pull independiente.
- Una invocación inicial de setup sin parada ante errores incluyó datos en un
  commit local propio. Antes de cualquier push se corrigió ese commit y sus tags:
  el historial entregado conserva los datos exclusivamente con DVC. El bundle se
  construye sólo con referencias alcanzables y se verifica que no incluya CSV
  masivos. No se sobreescribió trabajo preexistente del usuario.
- Los logs `publicacion-hf.log` y `github-privacidad.log` registran los bloqueos
  reales de autenticación/configuración. No prueban publicación ni recuperación HF.
- La recuperación independiente con DVC y nuevo venv pasó; el resultado global
  quedó como `passed=false` porque faltaban revisiones Hugging Face publicadas.
  Cualquier comprobación local suplementaria se identifica por separado.
