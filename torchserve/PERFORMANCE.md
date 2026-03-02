# TorchServe – note sulle performance

Le impostazioni in `config.properties` / `config.local.properties` sono state ottimizzate in base al [case study PyTorch per Animated Drawings](https://pytorch.org/blog/torchserve-performance-tuning/).

## Cosa è stato impostato

- **`default_workers_per_model=1`** – Per questo tipo di modelli (detector + pose estimator) 1 worker per modello riduce contention e spesso offre la latenza migliore.
- **`number_of_gpu=1`** – Un solo GPU per entrambi i modelli (round-robin). Con 2 GPU puoi impostare `number_of_gpu=2`.
- **`batchSize=1` e `maxBatchDelay=50`** – Orientati a **bassa latenza** (risposta più veloce per singola richiesta).
- **`number_of_netty_threads=4`** – Più thread frontend per gestire le connessioni in ingresso.

## Se preferisci più throughput (più richieste al secondo)

In `config.properties` (e in `config.local.properties` se usi lo script locale) puoi provare:

- `batchSize`: **4** o **8**
- `maxBatchDelay`: **100** (ms)

Esempio per un solo modello:

```properties
"batchSize": 4,\
"maxBatchDelay": 100\
```

La latenza per singola richiesta può aumentare un po’, ma il throughput migliora.

## GPU

Il case study mostra che su **GPU** la latenza è circa **13×** migliore che su CPU. Per prestazioni accettabili serve eseguire TorchServe con GPU (es. `docker run ... --gpus all`).

---

## Perché non tutto può andare su GPU

La pipeline fa più fasi; solo una parte è oggi sulla GPU:

| Fase | Dove gira oggi | Si può spostare su GPU? |
|------|-----------------|--------------------------|
| **Detector + Pose** (TorchServe) | GPU (CUDA) | Già su GPU. |
| **Rendering** (mesh, texture → frame) | CPU (Mesa/OSMesa) | In teoria sì (OpenGL/EGL), ma in Docker si usa Mesa in headless (`AD_USE_MESA=1`). Usare la GPU per il rendering richiederebbe supporto EGL/OpenGL nel codice della “view” di AnimatedDrawings (non esposto in questo repo). |
| **Retargeting** (motion → personaggio) | CPU (Python/NumPy) | Sì solo riscrivendo la logica con CuPy o PyTorch; lavoro non banale. |
| **Encoding GIF** | CPU | Non esiste uno standard per “GIF su GPU”; l’encoding resta su CPU. |

Quindi **non è possibile**, con le modifiche solo in questo repo, spostare “tutto” sulla GPU: la parte pesante dell’inferenza è già su GPU; il resto (rendering, retargeting, GIF) è intrinsecamente CPU o richiederebbe cambi profondi nel progetto AnimatedDrawings (view, retarget, encoder).

**Rendering su GPU in locale (Windows/Linux con display):**  
Per usare OpenGL sulla GPU invece di Mesa (CPU) durante la fase di rendering:

1. **Variabili d’ambiente**
   - `AD_USE_MESA=0` → usa WindowView (OpenGL GPU) invece di MesaView (CPU).
   - `AD_HEADLESS=1` → finestra nascosta (nessuna finestra a schermo), adatto a script e pipeline.

2. **Esempio**
   ```powershell
   $env:AD_USE_MESA = "0"
   $env:AD_HEADLESS = "1"
   python measure_pipeline.py path\to\image.png
   ```
   Lo script `measure_pipeline.py` imposta già queste variabili di default se non le definisci (per misurare con GPU).

3. **Docker:** nel container resta `AD_USE_MESA=1` (Mesa/CPU) perché non c’è display. Per usare la GPU nel rendering in Docker servirebbe un contesto EGL/headless (non implementato qui).

---

## Misurare i tempi (dove va il tempo)

La pipeline è divisa in due fasi misurate in `pipeline.py`:

1. **`image_to_annotations`** – TorchServe (detector + pose) → tempo su **GPU**.
2. **`annotations_to_animation`** – retarget + render + GIF → tempo su **CPU**.

**Dalla root del repo** (con TorchServe già avviato, es. in Docker):

```bash
set ANIMATED_DRAWINGS_ROOT=D:\path\to\AnimatedDrawings
python measure_pipeline.py path/to/tua_immagine.png
```

Oppure avvia l’app desktop, elabora un’immagine e guarda la **console** dove gira l’app: viene stampata una riga tipo:

```text
[Pipeline timing] image_to_annotations (TorchServe): X.XXs | annotations_to_animation (retarget+render+GIF): X.XXs | total: X.XXs
```

- Se **image_to_annotations** è la parte più lunga → il collo di bottiglia è TorchServe (già su GPU; si può provare batch/worker).
- Se **annotations_to_animation** è la parte più lunga → il collo di bottiglia è retarget/render/GIF su CPU (vedi tabella sopra).

**Dettaglio animazione:** alla fine del rendering viene stampata una riga `[Animation breakdown]` con i secondi per fase: **retarget**, **render**, **read+queue**, **write_file** (GIF/MP4). Serve a capire dove intervenire (es. se write_file domina, il GIF è lento; se retarget domina, si può valutare CuPy/PyTorch).

**Per stare sotto ~10 s:** (1) **Cache BVH**: dalla seconda animazione in poi (stesso processo) il BVH non viene ri-parsato → fase "scene" molto più veloce. (2) **MP4** (opzionale): `AD_OUTPUT_MP4=1` scrive `video.mp4` (encode più veloce, ~1 s in meno); l’MP4 non supporta la trasparenza, quindi il default resta GIF.

## Applicare le modifiche

- **Docker**: dopo aver cambiato `config.properties` ricostruisci l’immagine e riavvia il container.
- **Locale** (`start_torchserve.sh`): usa `config.local.properties`; riavvia TorchServe dopo le modifiche.

## Riferimenti

- [TorchServe Performance Tuning – Animated Drawings](https://pytorch.org/blog/torchserve-performance-tuning/)
- [TorchServe Configuration](https://pytorch.org/serve/configuration.html)
- [TorchServe Performance Guide](https://pytorch.org/serve/performance_guide.html)
