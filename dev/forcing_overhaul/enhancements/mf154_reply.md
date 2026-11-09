On the min depth question: not through the topo file. `write_topo_file` writes the masked depth, with land set to `land_fillval` (0 by default), so land heights aren't kept there. A negative min depth would also turn low-lying land into ocean, because cells count as ocean where depth > min_depth.

The `Topo` object does keep the raw interpolated depth (`topo.depth`, land as negative values when the source has land heights, as GEBCO does). Changing `topo.min_depth` later re-derives the mask from it, unless a manual mask has been set. To keep the heights on disk, save `topo.depth` separately.

The GridSketcher requests are on its roadmap, to pick up once its core is merged.
