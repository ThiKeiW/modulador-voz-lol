# 07 - Importar modelos custom (ej. Ultimate RVC)

Los personajes extra se entrenan **fuera** de la app (Ultimate RVC) y se
importan con Archivo -> Importar Modelo... Quedan en el grupo
**PERSONALIZADOS** del panel, listos sin reiniciar.

## Que archivos tomar de Ultimate RVC

1. **`.pth` (obligatorio)**: el modelo, normalmente en la carpeta
   `weights/` con el nombre del personaje (ej. `Garen.pth`).
2. **`.index` (opcional)**: solo si lo generaste (`added_*.index`).
   Sin indice funciona igual, con algo menos de calidad
   (igual que Briar/Yuumi, que no tienen).

## Regla `.pth` vs `.pth`+`.index`

| Caso | Resultado |
|------|-----------|
| Solo `.pth` | Funciona con `index_rate=0`, distintivo "sin índice" |
| `.pth` + `.index` | Retrieval activado, mejor fidelidad al personaje |

## En el dialogo de importacion

1. Examinar y elegir el `.pth` -> la app valida que sea checkpoint RVC
   real y muestra version/pitch/tasa (si dice "no valido", ese archivo
   no sirve).
2. Examinar el `.index` si lo tienes (o Quitar para dejarlo vacio).
3. Nombre (+ descripcion opcional) -> Importar.

## Alternativa manual (mismo resultado)

```
models/custom/<nombre>/
  modelo.pth
  added_XXX.index   (opcional)
  metadata.json     (opcional: name/game/language)
```

Al arrancar (o importar) se detecta solo. Para eliminar: boton ✕ del
personaje en el panel (pide confirmacion y borra la carpeta).

## Si algo falla al importar

- "No es un checkpoint RVC": el `.pth` elegido no trae keys
  `weight`/`config` (archivo corrupto o de otro formato).
- Checkpoints de **Ultimate RVC**: traen clases propias pickladas
  (`ultimate_rvc.typing_extra.TrainingSampleRate`) que `torch.load`
  normal rechaza. La app los convierte sola al importar
  (`core/ckpt_compat.py`) y guarda copia normalizada; no necesitas
  nada de Ultimate RVC instalado.
- El personaje no aparece: revisa el log de la app; el registro exige
  al menos un `.pth` en su carpeta.
