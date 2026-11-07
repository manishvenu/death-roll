"""Same as v1 but with the overlap test patched (raw lat + circular lon window)."""
import inspect, textwrap, runpy, sys
from pathlib import Path
from mom6_forge import mapping

src = inspect.getsource(mapping.generate_ESMF_map_via_xesmf)
old = src[src.index("        dst_mesh_lon = normalize_deg"):src.index("    dst_is_cyclic_x")]
new = '''        dst_mesh_lon = normalize_deg(dst_mesh["nodeCoords"].data[:, 0])
        dst_mesh_lat = dst_mesh["nodeCoords"].data[:, 1]
        s = np.unique(dst_mesh_lon)
        gaps = np.diff(np.r_[s, s[0] + 360.0])
        k = int(np.argmax(gaps))
        start, width = s[(k + 1) % s.size], 360.0 - gaps[k]
        lat_min, lat_max = dst_mesh_lat.min(), dst_mesh_lat.max()
        src_lon = normalize_deg(src_grid["lon"].data)
        src_lat = src_grid["lat"].data
        inside = (np.mod(src_lon - start, 360.0) <= width) & (src_lat >= lat_min) & (src_lat <= lat_max)
        src_grid["mask"].data = np.where(inside, src_grid["mask"].data, 0)

'''
assert old in src
exec(compile(src.replace(old, new), mapping.__file__, "exec"), mapping.__dict__)
print("patched generate_ESMF_map_via_xesmf")
runpy.run_path(str(Path(__file__).parent / "v1_overlap.py"), run_name="__main__")
