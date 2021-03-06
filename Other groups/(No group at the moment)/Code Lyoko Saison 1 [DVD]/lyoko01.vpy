import vapoursynth as vs
import lvsfunc as lvf
import kagefunc as kgf
import mvsfunc as mvf
import fvsfunc as fvf
import havsfunc as hvf
import vardefunc as vrdf
import modfunc as mdf
import functools
from nnedi3_rpow2CL import nnedi3_rpow2CL

import acsuite
ac = acsuite.AC()

core = vs.core
core.max_cache_size = 32000

def detelecine(src):
    def _postprocess(n, f, clip, deinterlaced):
        if f.props['_Combed'] > 0:
           return deinterlaced
        else:
           return clip    
    matched = core.vivtc.VFM(src, 1)
    src = core.nnedi3.nnedi3(src, field=1)
    return core.std.FrameEval(matched, functools.partial(_postprocess, clip=matched, deinterlaced=src), prop_src=matched)

src = lvf.src(r"RAW/Code.Lyoko.S01E01.DVD.Remux.Multi-Odd_HD.mkv")
src = core.std.AssumeFPS(src, fpsnum=25, fpsden=1)

asrc = r"AUDIOS/Code.Lyoko.S01E01.DVD.Remux.Multi-Odd_HD.mka"
ac.eztrim(src, [(3,34778)], asrc, "AUDIOS/S01E01_cut.mka")

src = src[3:34778]
src = core.std.FreezeFrames(src, first=[0], last=[1], replacement=[2])
src = detelecine(src)
src = fvf.Depth(src, 16)

conv = core.resize.Bicubic(src, transfer_in_s="470bg", primaries_in_s="470bg", matrix_in_s="470bg", transfer_s="709", primaries_s="709", matrix_s="709", dither_type="error_diffusion")

crop_a = core.std.CropRel(conv, left=10, top=2, right=8, bottom=2)
crop_b = core.std.CropRel(conv, left=10, top=18, right=8, bottom=18)
fixedges_a = core.edgefixer.ContinuityFixer(crop_a, [2, 1, 1], [6, 3, 3], [2, 1, 1], [6, 3, 3])
fixedges_b = core.edgefixer.ContinuityFixer(crop_b, [2, 1, 1], [6, 3, 3], [2, 1, 1], [6, 3, 3])
fixedges_b = core.resize.Bicubic(fixedges_b, 702, 572)
fixedges = fvf.rfs(fixedges_a, fixedges_b, mappings="[4859 4937] [4998 5201] [5321 5405] [5602 5659] [19680 19785] [20997 21125] [21176 21215]")

deblock = fvf.AutoDeblock(fixedges)
deblock32 = fvf.Depth(deblock, 32)

adaptmask = vrdf.adaptive_mask(deblock, 50)
edgemask = kgf.retinex_edgemask(deblock).std.Binarize(9500).std.Inflate()
w2x = mvf.ToRGB(deblock32, matrix="709")
w2x = core.w2xc.Waifu2x(w2x, noise=3, scale=1, gpu=1)
w2x = mvf.ToYUV(w2x, css='420', depth=16)
denoise_a = mdf.hybriddenoise_mod(deblock32, knl=0.5, sigma=2, depth=16)
denoise_b = mdf.hybriddenoise_mod(deblock32, knl=0.8, sigma=2.5, depth=16)
denoise_c = mdf.hybriddenoise_mod(deblock32, knl=1, sigma=3.5, depth=16)
denoise = core.std.MaskedMerge(denoise_b, denoise_c, adaptmask)
denoise = core.std.MaskedMerge(denoise, denoise_a, edgemask)
denoise = fvf.rfs(denoise, denoise_a, mappings="[4619 4858]")
denoise = fvf.rfs(denoise, w2x, mappings="[176 372] [467 470] [599 604] [720 724] [836 838] [926 929] [1028 1030]") #OP
denoise = fvf.rfs(denoise, w2x, mappings="[2555 2556] [2571 2572] [5714 5724] 11158") #Frames around some keyframes

dehalo = hvf.FineDehalo(denoise, rx=2, thmi=80, thma=128, thlimi=50, thlima=100, darkstr=0.4, brightstr=1.0)

dering = hvf.HQDeringmod(dehalo, mrad=2, msmooth=2, mthr=80, minp=2, nrmode=2, drrep=13, thr=64, sharp=3, darkthr=0.3, planes=[0, 1, 2])

resize = nnedi3_rpow2CL(dering, device=0).resize.Bicubic(768, 576, format=vs.YUV420P16, filter_param_a=0, filter_param_b=1/2)

aa = lvf.upscaled_sraa(resize, 1.5, 13, sharp_downscale=False)

deband_a = core.f3kdb.Deband(aa, range=15, y=44, cb=44, cr=44, grainy=32, grainc=0, output_depth=16)
deband_b = core.f3kdb.Deband(aa, range=15, y=50, cb=50, cr=50, grainy=32, grainc=0, output_depth=16)
deband_c = core.f3kdb.Deband(aa, range=17, y=64, cb=64, cr=64, grainy=32, grainc=0, output_depth=16)
deband = fvf.rfs(deband_a, deband_b, mappings="[1125 1249]")
deband = fvf.rfs(deband, deband_c, mappings="[11158 11214]")

grain_a = kgf.adaptive_grain(deband, 0.2)
grain_b = core.grain.Add(deband, var=0.4, constant=True)
grain_b = core.grain.Add(grain_b, var=0.8, constant=False)
grain_c = core.grain.Add(deband, var=1.2, constant=False)
grain = fvf.rfs(grain_a, grain_b, mappings="[176 372] [4525 4618]") #Lyoko Connection 
grain = fvf.rfs(grain, grain_c, mappings="[1125 1249]") #Title

final = fvf.Depth(grain, 10)

final.set_output()