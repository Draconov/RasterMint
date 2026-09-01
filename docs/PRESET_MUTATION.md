# Preset Mutation

RasterMint 0.7.0 adds controlled **Preset Mutation** to the Presets inspector.

Select any built-in, user, or extension preset, then use the **Preset Mutation** panel to choose the number of variants and Mutation Amount and press **Mutate**. RasterMint generates **6–12 nearby variations** and renders normal current-image preset thumbnails for them. The generated looks appear in a dynamic **Mutations** category placed after the normal preset categories.

## What is preserved

Mutation deliberately preserves the preset's editable structure:

- layer count, order, kind, IDs, enable state, blend modes, and masks;
- animation tracks;
- target raster and other structural settings;
- locked palette colours.

It makes bounded changes to suitable numeric effect parameters, layer opacity, and unlocked palette colours. Choice parameters such as algorithms, display modes, fonts, text, seeds, JSON data, and custom matrices are not randomly replaced.

Selecting a generated variation applies ordinary RasterMint settings. Nothing is flattened or baked, so every layer and parameter can still be edited, animated, reordered, saved to the preset library, or stored in a `.rastermint` project.

Mutation generation is intentionally different from Creative Randomize: it explores the neighbourhood of one chosen preset instead of constructing a largely unrelated look.
