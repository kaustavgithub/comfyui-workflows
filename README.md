# comfyui-workflows

Our ComfyUI node packs and workflows, kept apart from the image
([comfyui-image](https://github.com/kaustavgithub/comfyui-image): ComfyUI,
PyTorch and the Python packages the nodes need). A change here needs no image
build.

- `nodes/<pack>/`: custom node packs. Each is linked into ComfyUI's
  `custom_nodes` at start. `comfyui-documentary`: photos -> a narrated
  documentary video or reel (see its `__init__.py`), with its fonts
  (`fonts/`, open licences in `LICENSE-*.txt`) and its template
  ("Documentary from photos", in ComfyUI's template browser).
- `workflows/*.json`: workflows copied into ComfyUI's workflows list when it
  doesn't have one of that name yet. ComfyUI owns them after that: what you
  save there is never overwritten. To keep an edit in Git:
  `scripts/export-workflow.sh "Documentary - Reel job"`, then commit.
  The cron jobs (Airflow `youtube_film`, `instagram_reel`) read
  "Documentary - YouTube job" and "Documentary - Reel job" from ComfyUI at
  every run.

## comfyui-documentary

- Photos →
  per photo, a vision model names the subject and a text model (both through
  the homelab's LLM gate, OpenAI API: `DOC_LLM_URL`, `DOC_LLM_TOKEN`)
  writes the narration → Chatterbox or Kokoro text-to-speech → music → video
  with an intro, transitions, subtitles and a follow card, plus a
  thumbnail and a social post (caption, hashtags, key phrases), for a
  YouTube video (16:9) or an Instagram reel (9:16, at most 90 s). Template
  "Documentary from photos" in ComfyUI's template browser.
- Species: BioCLIP 2 (open_clip, `species.py`) names a bird's or mammal's
  species when it is sure, among the world's birds and mammals (GBIF; no
  location is used), weighted by how common each one is; a name given on the
  photo, or a species named in its note, wins. Unsure: the story says only "a
  duck" and uses no facts. The facts are each species' Wikipedia intro,
  downloaded once with the list into `/data/models/bioclip`; a narration's
  number that neither they, the note nor the camera settings have is
  rewritten or dropped.
- Stories open with a hook line. Mood "behind the lens": the photographer's
  own story of each shot, from its camera settings and time. Your own voice
  (my_voice) speaks calmly in every mood, close to the recording.
- Offline: the documentary nodes send no photo, note or story anywhere but the
  LLM gate. Their models load from the volume without asking Hugging Face for
  updates, and the facts are on the volume too: once each file has been
  downloaded (on its first use), a workflow runs without the internet. The
  only requests out are those one-time downloads (model weights; the
  species list and facts, asked by scientific names).
- Editable in the workflow: Documentary Prompts (every prompt sent to the
  LLMs, with the built-in text) and Documentary Look (fonts, accent colour,
  intro, subtitles, colour grade, finish, follow card, thumbnail layout; each
  "auto (from mood)", random per film, or fixed).
- Its Python packages (Kokoro, Chatterbox, open_clip) are in the image.

## How it gets into ComfyUI

The homelab's gitops (`apps/comfyui/`) pins a commit of this repo
(`WORKFLOWS_REF`). At every start an init container fetches that commit to
`/data/repos/comfyui-workflows`, links each node pack and seeds the missing
workflows. To ship a change: push here, set the new commit in gitops; ArgoCD
restarts ComfyUI with it (Python nodes load only at start). Roll back: the
old commit.

A new pack whose Python packages aren't in the image: install them with the
Manager (they go to the volume's `/data/venv`), or add them to the image.
