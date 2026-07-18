# Web export

Godot version: `4.3.0`.

After installing that pinned editor, export same fixture with:

```sh
godot --headless --path showcase/godot-deckbuilder \
  --export-release Web showcase/godot-deckbuilder/web/index.html
```

The generated `web/` directory is release output, not detector input. Release verification
must confirm it was generated from this fixture commit before publishing the showcase.
