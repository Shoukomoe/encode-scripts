import vapoursynth as vs
core = vs.get_core()
import mvsfunc as mvf
import kagefunc as kgf
import fvsfunc as fvf
import lvsfunc as lvf
import vardefunc as vrdf
from vsutil import get_w, split, join
core.max_cache_size = 32000

src = lvf.src(r'island09.m2ts')[:34047]
src = fvf.Depth(src, 16)

opstart = 8128

flashback = '[17994 18081] [21573 22880]'

y, u, v = split(src)

descaled = kgf.inverse_scale(y, height=720, kernel='bicubic', b=1/5, c=1/2, mask_detail=True)
descaled = fvf.Depth(descaled, 16)

adaptmask = vrdf.adaptive_mask(descaled, 300)
edgemask = kgf.retinex_edgemask(descaled, 1)
denoise_a = mvf.BM3D(descaled, 1.2)
denoise_b = mvf.BM3D(descaled, 2.1)

denoise = core.std.MaskedMerge(denoise_a, denoise_b, adaptmask)
denoise = core.std.MaskedMerge(denoise, descaled, edgemask)

denoise = fvf.rfs(denoise, denoise_b, mappings=flashback + f"[{opstart+1381} {opstart+1430}]")

aa = lvf.upscaled_sraa(denoise, 2, 13)

scaled_u = core.resize.Bicubic(u, get_w(720), 720, src_left=0.25)
scaled_v = core.resize.Bicubic(v, get_w(720), 720, src_left=0.25)

merged = join([aa, scaled_u, scaled_v])

adaptmask = vrdf.adaptive_mask(merged, 300)
edgemask = kgf.retinex_edgemask(merged, 1)
deband_a = fvf.GradFun3(merged, smode=2, thr=0.15,radius=13)
deband_b = fvf.GradFun3(merged, smode=2, thr=0.35,radius=15)
deband_c = core.f3kdb.Deband(merged, range=15, y=34, cb=26, cr=26, grainy=16, grainc=0, output_depth=16)
deband_c = core.std.MaskedMerge(deband_c, merged, edgemask)
deband = core.std.MaskedMerge(deband_a, deband_b, adaptmask)
deband = core.std.MaskedMerge(deband, merged, edgemask)
deband = fvf.rfs(deband, deband_c, mappings=flashback)

grain_a = kgf.adaptive_grain(deband, 0.3, luma_scaling=16)
grain_b = kgf.adaptive_grain(deband, 0.8, luma_scaling=6, static=False)
grain_c = core.grain.Add(deband, var=0.85, constant=False)
grain = fvf.rfs(grain_a, grain_b, mappings=f"[{opstart+1381} {opstart+1430}]")
grain = fvf.rfs(grain, grain_c, mappings=flashback)

final = fvf.Depth(grain, 10)

final.set_output()