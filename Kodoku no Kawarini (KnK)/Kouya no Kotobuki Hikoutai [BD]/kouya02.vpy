import vapoursynth as vs
import lvsfunc as lvf
import kagefunc as kgf
import mvsfunc as mvf
import fvsfunc as fvf
import vardefunc as vrdf
import vsTAAmbk as taa
from nnedi3_rpow2 import nnedi3_rpow2
from vsutil import get_y, get_w

core = vs.core
core.max_cache_size = 64000

src = lvf.src(r"Vol.01/BDMV/STREAM/00003.m2ts")[:34046]
src = fvf.Depth(src, 16)

opstart, opend = 360, 2517
eye_start, eye_end = 14433, 14480
edstart, edend = 31528, 33685
edendJikai = 33721
titreend = 33980
end = src.num_frames-1

fixedges_a = core.edgefixer.ContinuityFixer(src, [1,0,0], [1,0,0], [1,0,0], [1,0,0])
fixedges_b = core.edgefixer.ContinuityFixer(src, [1,0,0], 0, [1,0,0], 0)
fixedges = fvf.rfs(fixedges_a, fixedges_b, mappings=f'[{opstart} {opend}] [{edstart} {edend}]')
fixedges = fvf.rfs(fixedges, src, mappings=f'[{edend+1} {edendJikai}] [{eye_start} {eye_end}] [{titreend} {end}]')

descaled = core.descale.Debicubic(fvf.Depth(get_y(fixedges), 32), get_w(844), 844, 0, 1/2)

denoise_mask = vrdf.adaptive_mask(descaled, 10)
denoise_a = mvf.BM3D(descaled, sigma=0.35, radius1=1)
denoise_b = mvf.BM3D(descaled, sigma=0.75, radius1=1)
denoise = core.std.MaskedMerge(denoise_b, denoise_a, denoise_mask)
denoise = fvf.Depth(denoise, 16)

db_y_a, db_c_a = vrdf.F3kdbSep(denoise, src, 16, 36, 24, 0, 0)
db_y_b, db_c_b = vrdf.F3kdbSep(denoise, src, 18, 42, 38, 0, 0)
db_y = fvf.rfs(db_y_a, db_y_b, mappings='[15876 16205] [18282 18398] [29938 30001]')
db_c = fvf.rfs(db_c_a, db_c_b, mappings='[15876 16205] [18282 18398] [29938 30001]')

aa = taa.TAAmbk(db_y, aatype='Eedi3', alpha=0.2, beta=0.25, gamma=1000, nrad=2, mdis=15, mtype=1, mpand=(2,2), sharp=60)

scaled = nnedi3_rpow2(aa, nns=4).resize.Bicubic(1920, 1080, filter_param_a=0, filter_param_b=0)

merged = core.std.ShufflePlanes([scaled, db_c], [0, 1, 2], vs.YUV)

c_mask = vrdf.DRM(fixedges, 844, 'bicubic', b=0, c=1/2, mthr=150, mode='ellipse', sw=4, sh=4).std.Inflate()
credit = fvf.rfs(merged, core.std.MaskedMerge(merged, fixedges, c_mask), mappings=f'[{opstart} {opend}] [{eye_start} {eye_end}] [{edstart} {edend}]')

grain_a = kgf.adaptive_grain(credit, 0.2, luma_scaling=8)
grain_b = kgf.adaptive_grain(credit, 0.4, luma_scaling=8)
grain = fvf.rfs(grain_a, grain_b, mappings='[15876 16205] [18282 18398] [29938 30001]')

final = fvf.Depth(grain, 10)

final.set_output()