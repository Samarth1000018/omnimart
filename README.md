# OmniMart AI

Browser-first autonomous checkout prototype. The web app runs TensorFlow.js in the browser, the FastAPI service stores visits in local SQLite, and Streamlit provides store views. All payment methods are simulations; this project does not charge a payment instrument.

## Start the demo

1. Start the API:

   ```powershell
   cd omnimart-phase1
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

   Startup creates `omnimart.db` and seeds the catalog, including a demo smartphone item so COCO-SSD's `cell phone` detection can be tested end to end. API docs are at `http://localhost:8000/docs`.
2. Open `http://localhost:8000/`. FastAPI serves the checkout site there (and at `/smart-checkout/`); the CCTV analyser is at `http://localhost:8000/cctv_analyser.html`. Camera access works on localhost. To serve the static pages separately, you can also run `python -m http.server 8080` from the repository root.
3. Optional dashboard dependencies: `pip install -r requirements-dashboard.txt`, then run `streamlit run dashboard.py` from the repository root. Use `streamlit run omnimart-phase2/dashboard_phase2.py` for the phase-two CSV review.
4. Open `cctv_analyser.html` to upload and analyse a recording. Install `requirements-training.txt`, then use `python collect_images.py <label>` to collect training samples; press SPACE to save and Q to quit.

## Project map

- `smart-checkout/` — standalone HTML/CSS/JS checkout with live camera, uploaded video, catalog/cart, and simulated payment flow.
- `cctv_analyser.html` — recorded video detection timeline and CSV export.
- `omnimart-phase1/app/` — FastAPI, SQLAlchemy async models, seed data, and JWT exit verification.
- `omnimart-phase2/tracker.py` — in-memory digital-twin prototype and four explainable review signals.
- `dashboard.py`, `omnimart-phase2/dashboard_phase2.py` — phase-one operations dashboard and phase-two CSV review dashboard.
- `collect_images.py` — OpenCV webcam capture organized by class label.

## API

All application routes are under `/api`. The nine routes are `GET /health`, `GET /products`, `POST /sessions`, `GET /sessions`, `POST /sessions/{id}/cart`, `DELETE /sessions/{id}/cart/{product_id}`, `POST /sessions/{id}/events`, `POST /sessions/{id}/checkout`, and `POST /exit/verify?token=…`. Set `OMNIMART_DATABASE_URL` to change the async SQLAlchemy URL, `OMNIMART_JWT_SECRET` to set the signing secret, and `OMNIMART_CORS_ORIGINS` to restrict CORS origins. Defaults are for local development only.

## Detection model notes

The default browser detector is COCO-SSD MobileNet v2. COCO-SSD recognizes general COCO object classes, not retail SKUs, so its item-to-product mapping is only a demonstration. Bring a custom TensorFlow.js GraphModel by entering its `model.json` URL in the checkout UI. The current adapter expects YOLOv8-style raw output shaped `[1,84,N]` or `[1,N,84]` with 640×640 input, normalized float pixels, center-xywh boxes, and 80 COCO class scores. Export a compatible model or adapt the small `yoloDetect` function for your model's input/output contract and labels. The upload analyser uses COCO-SSD and reports visible detections; it does not infer identity or prove a pickup.

## Phase-two limits

The tracker is a state/alert prototype; a person or object tracker must provide stable track IDs, zone transitions, carry/conceal actions, and product IDs. The four signals need human review and are not findings of theft. State currently lives in process memory. No face recognition or identity database is included.
