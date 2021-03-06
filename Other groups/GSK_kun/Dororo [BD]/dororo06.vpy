import vapoursynth as vs
import lvsfunc as lvf
import kagefunc as kgf
import havsfunc as hvf
import fvsfunc as fvf
import vsTAAmbk as taa
import vardefunc as vrdf
import descale as dsc
import debandshit as dbs
import modfunc as mdf
import acsuite
from edi_rpow2 import znedi3_rpow2
from cooldegrain import CoolDegrain
from vsutil import get_w

core = vs.core
core.max_cache_size = 26000
core.num_threads = 18

ac = acsuite.AC()

src = lvf.src(r'[BDMV] どろろ Blu-ray BOX/上巻/DORORO_1/BDMV/STREAM/00006.m2ts')

asrc = r'[BDMV] どろろ Blu-ray BOX/上巻/DORORO_1/BDMV/STREAM/00006.mka'
ac.eztrim(src,[(24,34191)], asrc,"dororo06.mka")

src = src[24:34191]

# Keyframes for x264 --qpfile 
vrdf.generate_keyframes(src, 'dororo06_keyframes.log')

# Frame variables
opstart, opend = 1574, 3716 # opstart: first frame with light
epnamestart, epnameend = opend+1, 3812
edstart, edend = 31889, 34046
cardstart, cardend = edend+1, src.num_frames-1

# Zones
opening = f'[{opstart} {opend}]'
opening_a = f'[{opstart+754} {opstart+797}] [{opstart+1299} {opstart+1314}]'
opening_b = f'[{opstart+2005} {opstart+2043}]'

# Dither
src32 = fvf.Depth(src, 32)
src16 = fvf.Depth(src, 16)

# Descale
desc = dsc.Descale(src16, get_w(806), 806, 'bicubic', 0, 1/2, gray=True)

# Luma noise stabilization
den_clip = core.knlm.KNLMeansCL(desc, a=2, h=0.35, d=1, device_type='gpu')
stab = hvf.GSMC(desc, den_clip, radius=3)

# Luma adaptive denoise for episodes
adapt_m = vrdf.adaptive_mask(desc, 30)
den_y_a = CoolDegrain(stab, tr=1, thsad=72, thsadc=0, bits=16, blksize=8, overlap=4)
den_y_b = CoolDegrain(stab, tr=1, thsad=48, thsadc=0, bits=16, blksize=8, overlap=4)
den_y = core.std.MaskedMerge(den_y_a, den_y_b, adapt_m)

# Just a standard chroma denoise
den_uv = core.knlm.KNLMeansCL(src32, a=2, h=0.6, d=3, device_type='gpu', channels='UV')

# Rescaling & merge luma/chroma
scaled_y = vrdf.Bicubic(znedi3_rpow2(den_y, 2, nns=4, qual=2), 1920, 1080, 'catrom')
scaled = core.std.ShufflePlanes([scaled_y, fvf.Depth(den_uv, 16)], [0, 1, 2], vs.YUV)

# Luma & chroma denoise without rescaling. Opening parts
adapt_m = vrdf.adaptive_mask(src16, 300)
den_a = mdf.hybriddenoise_mod(src32, knl=0.25, sigma=1, radius1=1)
den_b = mdf.hybriddenoise_mod(src32, knl=0.75, sigma=3, radius1=1)
den_b = core.std.MaskedMerge(src16, den_b, adapt_m)
den = fvf.rfs(src16, den_a, mappings=opening)
den = fvf.rfs(den, den_b, mappings=opening_a)

# Opening anti-aliasing & scenefiltering
aa_a = lvf.upscaled_sraa(den, rep=13, sharp_downscale=False)
aa_a = taa.TAAmbk(aa_a, aatype=0, aatypeu='Nnedi3', aatypev='Nnedi3')
scaled = fvf.rfs(scaled, aa_a, mappings=opening)

# Deband masks
scaled8 = fvf.Depth(scaled, 8)
line_m_a = taa.TAAmbk(scaled8, mtype=1, showmask=1).std.Inflate()
line_m_b = kgf.retinex_edgemask(scaled8).rgvs.RemoveGrain(3).rgvs.RemoveGrain(3).std.Inflate().std.Inflate()
line_m = core.std.Expr([line_m_a, line_m_b], 'x y +')
line_m = core.std.Expr(line_m, 'x 30 < 0 x 3 * ?').std.Inflate().std.Inflate()
adapt_m = vrdf.adaptive_mask(scaled, 60)

# Deband & scenefiltering
db_a = core.neo_f3kdb.Deband(scaled, 17, 42, 48, 48, 24, 0, sample_mode=4)
db_b = core.neo_f3kdb.Deband(scaled, 14, 48, 54, 54, 32, 0, sample_mode=4)
db_c = core.neo_f3kdb.Deband(scaled, 17, 36, 36, 36, 24, 0, sample_mode=4)
db_d = core.neo_f3kdb.Deband(scaled, 14, 64, 76, 76, 32, 0, sample_mode=4)
db_e = dbs.f3kbilateral(scaled, 23, 500, 500)
db_e = core.std.MaskedMerge(db_e, scaled, fvf.Depth(line_m_a, 16))
db_e = core.grain.Add(db_c, 0.2)
db_f = dbs.f3kbilateral(scaled, 20, 90, 120)
db_g = dbs.f3kbilateral(src16, 22, 110, 110)
db_h = dbs.f3kbilateral(src16, 23, 220, 220)

db = core.std.MaskedMerge(db_a, db_b, adapt_m)
db = core.std.MaskedMerge(db, scaled, fvf.Depth(line_m, 16))

db = fvf.rfs(db, core.std.MaskedMerge(db_c, db_d, adapt_m), mappings=opening)
db = fvf.rfs(db, db_e, mappings=opening_a)
db = fvf.rfs(db, db_f, mappings=opening_b)
db = fvf.rfs(db, db_g, mappings='[17212 17325]')

# Grain & scenefiltering
grain_a = kgf.adaptive_grain(db, 0.25)
grain_b = kgf.adaptive_grain(db, 0.5)
grain_c = kgf.adaptive_grain(db, 0.8, luma_scaling=4)
grain_d = kgf.adaptive_grain(core.std.MaskedMerge(db_g, db_h, adapt_m), 0.4)
grain = fvf.rfs(grain_a, grain_b, mappings=opening_a)
grain = fvf.rfs(grain, grain_c, mappings=opening_b)
grain = fvf.rfs(grain, grain_d, mappings=f'[{edstart} {edend}]')

# Episode name & endcard
aa_b = lvf.upscaled_sraa(src16, 2, rep=13, sharp_downscale=False)
tag = fvf.rfs(grain, aa_b, mappings=f'[{epnamestart} {epnameend}] [{cardstart} {cardend}]')
tag = core.std.FreezeFrames(tag, epnamestart, epnameend, epnameend)
tag = core.std.FreezeFrames(tag, cardstart, cardend, cardend)

# Dither final
final = fvf.Depth(tag, 10)

final.set_output()