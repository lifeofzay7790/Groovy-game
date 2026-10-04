"""Unreal-only reference art pass. All generated actors use the builder's tag.

Uses only this manor's model kit and engine basic shapes. Shader animation runs
in packaged games too; it does not require an editor tick or downloaded effects.
"""
import math
import unreal


def _pulse(h, mat, speed=1.0, depth=0.12):
    time = h._expr(mat, unreal.MaterialExpressionTime, -900, 400)
    freq = h._expr(mat, unreal.MaterialExpressionMultiply, -750, 400, const_b=speed)
    wave = h._expr(mat, unreal.MaterialExpressionSine, -600, 400)
    amplitude = h._expr(mat, unreal.MaterialExpressionMultiply, -450, 400, const_b=depth)
    bias = h._expr(mat, unreal.MaterialExpressionAdd, -300, 400, const_b=1.0-depth)
    h._connect(time, freq, 'A'); h._connect(freq, wave)
    h._connect(wave, amplitude, 'A'); h._connect(amplitude, bias, 'A')
    return bias


def _effect_material(h, name, color, strength, water=False, light=False):
    mat, created = h._new_asset(name, h.ROOT+'/Materials/FX', unreal.Material, unreal.MaterialFactoryNew())
    if not created:
        return mat
    if light:
        mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_LIGHT_FUNCTION)
    else:
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
        mat.set_editor_property('two_sided', True)
    pulse = _pulse(h, mat, 0.65 if water else 2.7, 0.10 if water else 0.16)
    col = h._expr(mat, unreal.MaterialExpressionConstant3Vector, -300, 0,
                  constant=unreal.LinearColor(*(v*strength for v in color), 1))
    mult = h._expr(mat, unreal.MaterialExpressionMultiply, -80, 0)
    h._connect(col, mult, 'A'); h._connect(pulse, mult, 'B')
    h.MEL.connect_material_property(mult, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if not light:
        opacity = h._expr(mat, unreal.MaterialExpressionConstant, -80, 200, r=0.38 if water else 0.85)
        h.MEL.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    if water:
        # World-space travelling bands make the water move down every stream.
        wp = h._expr(mat, unreal.MaterialExpressionWorldPosition, -1200, -400)
        z = h._expr(mat, unreal.MaterialExpressionComponentMask, -1050, -400, r=False, g=False, b=True, a=False)
        scale = h._expr(mat, unreal.MaterialExpressionMultiply, -900, -400, const_b=0.045)
        time = h._expr(mat, unreal.MaterialExpressionTime, -1200, -200)
        speed = h._expr(mat, unreal.MaterialExpressionMultiply, -1050, -200, const_b=1.6)
        add = h._expr(mat, unreal.MaterialExpressionAdd, -750, -350)
        sine = h._expr(mat, unreal.MaterialExpressionSine, -600, -350)
        amp = h._expr(mat, unreal.MaterialExpressionMultiply, -450, -350, const_b=0.28)
        base = h._expr(mat, unreal.MaterialExpressionAdd, -300, -350, const_b=0.6)
        for a,b,pin in ((wp,z,''),(z,scale,'A'),(time,speed,'A'),(scale,add,'A'),
                        (speed,add,'B'),(add,sine,''),(sine,amp,'A'),(amp,base,'A')):
            h._connect(a,b,pin)
        h.MEL.connect_material_property(base, '', unreal.MaterialProperty.MP_OPACITY)
    h.MEL.recompile_material(mat); h.EAL.save_loaded_asset(mat)
    return mat


def _mesh(h, eas, mesh, label, pos, size, material, rotation=None):
    actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*pos), rotation or unreal.Rotator())
    actor.set_actor_scale3d(unreal.Vector(*(v/100 for v in size)))
    comp = actor.get_editor_property('static_mesh_component')
    comp.set_static_mesh(mesh); comp.set_material(0, material)
    comp.set_collision_profile_name('NoCollision'); comp.set_cast_shadow(False)
    comp.set_editor_property('can_ever_affect_navigation', False)
    h._finish(actor, 'LM_FX_'+label, 'FX', 'Effect')
    return actor


def _local(p, x, y, z):
    a=math.radians(p.rot[1]); sx,sy,sz=p.mesh_scale
    return (p.pivot[0]+x*sx*math.cos(a)-y*sy*math.sin(a),
            p.pivot[1]+x*sx*math.sin(a)+y*sy*math.cos(a),p.pivot[2]+z*sz)


def _light(h,eas,label,pos,color,intensity,radius,shadow=False,flicker=None):
    a=eas.spawn_actor_from_class(unreal.PointLight,unreal.Vector(*pos))
    c=a.get_editor_property('light_component'); c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',unreal.LightUnits.CANDELAS)
    c.set_intensity(intensity); c.set_attenuation_radius(radius)
    c.set_light_color(unreal.LinearColor(*color,1)); c.set_cast_shadows(shadow)
    c.set_editor_property('source_radius',8.0)
    c.set_editor_property('volumetric_scattering_intensity',0.25)
    if flicker: c.set_editor_property('light_function_material',flicker)
    h._finish(a,'PL_LM_Detail_'+label,'Lighting/Practical','Light')


def _dress(h,eas,prims,meshes,kit_mats):
    """Small objects on actual measured surfaces, not guessed design-unit heights."""
    extra=[]
    for p in prims:
        if p.mesh != 'SM_LM_Fireplace_01': continue
        for i,(x,y,z,model) in enumerate(((-145,35,348,'Candle_Pillar_02'),(-118,30,348,'Candle_Pillar_01'),
                                         (145,35,348,'Candle_Pillar_02'),(116,35,348,'Candle_Pillar_01'),
                                         (0,32,348,'CrownOrnament_01'))):
            name='SM_LM_'+model; info=h.lmk.KIT[name]
            q=h.lm.Prim('Mantel%s%d'%(p.label,i),'box',(0,0,0),info['size'],
                        rot=p.rot,mesh=name,pivot=_local(p,x,y,z),
                        offset=h.lm._OFFSETS[info['pivot']](*info['size']),collision='none',
                        folder='Props/MantelDetails',kind='MantelDetail')
            # Already in centimetres: do not scale this primitive a second time.
            h.spawn_prim(eas,q,meshes,{},_dress.kit_meshes,kit_mats,True); extra.append(q)
    return extra


def apply(h,eas,prims,meshes):
    h.EAL.make_directory(h.ROOT+'/Materials/FX')
    h.EAL.make_directory(h.ROOT+'/Materials/Reference')
    flame=_effect_material(h,'M_LM_CandleFlame',(1.0,0.32,0.035),18)
    water=_effect_material(h,'M_LM_FlowingWater',(0.015,0.3,1.0),6,water=True)
    flicker=_effect_material(h,'M_LM_CandleLightFunction',(1,1,1),1,light=True)
    # Reuse imported kit assets; the polish stage does not re-import geometry.
    _dress.kit_meshes={n:h.EAL.load_asset(h.ROOT+'/'+k['category']+'/'+n) for n,k in h.lmk.KIT.items()}
    extra=_dress(h,eas,prims,meshes,{})
    all_prims=list(prims)+extra
    by_label={'LM_'+p.label:p for p in all_prims}
    material_cache={}
    for actor in eas.get_all_level_actors():
        label=actor.get_actor_label()
        p=by_label.get(label)
        if p and p.mesh:
            comp=actor.get_editor_property('static_mesh_component')
            if 'Chandelier' in p.mesh or 'Chain' in p.mesh:
                comp.set_cast_shadow(False)
            cloth=any(t in p.mesh for t in ('Banner','Rug','Runner','Sofa','Chair','Ottoman','Stair_Grand'))
            # Authored navy and FX recolouring already preserve the gold details.
            if 'Navy' in p.mesh or (h.MOOD and h.FX_MATERIALS.get(p.mesh, {}).get('RecolorAmount', 0)):
                cloth=False
            stone=any(t in p.mesh for t in ('Wall_','Column_','StairStringer'))
            if cloth or stone:
                for i in range(comp.get_num_materials()):
                    parent=comp.get_material(i)
                    if not parent: continue
                    style='Navy' if cloth else 'WarmStone'
                    key=(parent.get_path_name(),style)
                    if key not in material_cache:
                        mi,_=h._new_asset('MI_'+parent.get_name()+'_'+style,h.ROOT+'/Materials/Reference',
                                          unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
                        h.MEL.set_material_instance_parent(mi,parent)
                        h.MEL.set_material_instance_scalar_parameter_value(mi,'ClothStrength',0.9 if cloth else 0)
                        h.MEL.set_material_instance_vector_parameter_value(mi,'Tint',
                            unreal.LinearColor(0.82,0.82,0.88,1) if cloth else unreal.LinearColor(0.60,0.53,0.43,1))
                        h.MEL.update_material_instance(mi); h.EAL.save_loaded_asset(mi)
                        material_cache[key]=mi
                    comp.set_material(i,material_cache[key])
        if label.startswith('PL_LM_'):
            c=actor.get_editor_property('light_component')
            if 'Chandelier' in label:
                c.set_intensity(c.get_editor_property('intensity')*0.42)
                c.set_editor_property('source_radius',35.0)
                c.set_light_color(unreal.LinearColor(1,1,1,1))
                c.set_editor_property('use_temperature',True); c.set_editor_property('temperature',3400.0)
            if 'Fireplace' in label or 'Sconce' in label:
                c.set_editor_property('light_function_material',flicker)
                c.set_editor_property('source_radius',12.0)
            if 'Sconce' in label:
                c.set_light_color(unreal.LinearColor(1,1,1,1))
                c.set_editor_property('use_temperature',True); c.set_editor_property('temperature',3000.0)
            c.set_editor_property('volumetric_scattering_intensity',0.25)
        if label=='PPV_LM_EntranceHall':
            pp=actor.get_editor_property('settings')
            for prop,val in (('auto_exposure_min_brightness',1.0),('auto_exposure_max_brightness',1.0),
                             ('auto_exposure_bias',-2.0),('bloom_intensity',0.35),('bloom_threshold',1.5),
                             ('vignette_intensity',0.22),('motion_blur_amount',0.0),
                             ('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN),
                             ('reflection_method',unreal.ReflectionMethod.LUMEN)):
                pp.set_editor_property('override_'+prop,True); pp.set_editor_property(prop,val)
            actor.set_editor_property('settings',pp)
    for p in all_prims:
        if not p.mesh: continue
        locs=[]
        if 'Candle_Pillar' in p.mesh: locs=[(0,0,p.size[2]+3)]
        elif 'Candelabra' in p.mesh:
            locs=[(0,0,p.size[2]),(-p.size[0]*0.32,0,p.size[2]*0.9),(p.size[0]*0.32,0,p.size[2]*0.9)]
            if not (h.MOOD and p.mesh in h.CANDLE_LIGHTS):
                _light(h,eas,p.label,_local(p,0,0,p.size[2]+5),(1.0,0.5,0.16),22,280,flicker=flicker)
        elif 'WallSconce' in p.mesh: locs=[(0,20,23)]
        elif 'Chandelier' in p.mesh:
            locs=[(80*math.cos(a*math.tau/8),80*math.sin(a*math.tau/8),-160) for a in range(8)]
        elif p.mesh=='SM_LM_Fire_01':
            locs=[(-35,0,28),(0,0,38),(35,0,24)]
        if h.MOOD and h.FX_MATERIALS.get(p.mesh, {}).get('GlowStrength', 0):
            locs=[]  # The imported flame surfaces already glow and flicker.
        for i,local in enumerate(locs):
            size=(12,12,28) if 'Fire_01' in p.mesh else (3,3,9)
            _mesh(h,eas,meshes['sphere'],p.label+'Flame'+str(i),_local(p,*local),size,flame)
        if p.mesh=='SM_LM_Fountain_01' and not any(
                q.mesh=='SM_LM_FountainWater_01' and q.pivot==p.pivot for q in prims):
            _mesh(h,eas,meshes['cyl'],p.label+'Pool',_local(p,0,0,118),(310,310,1.2),water)
            # Thin segmented arcs descend from the upper bowl into the basin.
            for i in range(24):
                angle=math.tau*i/24
                for j in range(6):
                    ends=[]
                    for t in (j/6,(j+1)/6):
                        r=68+65*t
                        ends.append(_local(p,r*math.cos(angle),r*math.sin(angle),246+18*math.sin(math.pi*t)-128*t*t))
                    a,b=ends; delta=[b[k]-a[k] for k in range(3)]
                    length=math.sqrt(sum(v*v for v in delta))
                    yaw=math.degrees(math.atan2(delta[1],delta[0]))
                    pitch=math.degrees(math.atan2(delta[2],math.hypot(*delta[:2])))-90
                    _mesh(h,eas,meshes['cyl'],p.label+'Stream%d_%d'%(i,j),
                          [(a[k]+b[k])/2 for k in range(3)],(1.8,1.8,length+0.6),water,
                          unreal.Rotator(pitch=pitch,yaw=yaw,roll=0))
    _light(h,eas,'MoonPortal',(1120,0,280),(0.3,0.48,1.0),380,1900,shadow=True)
    fog=eas.spawn_actor_from_class(unreal.ExponentialHeightFog,unreal.Vector(0,0,-100))
    fc=fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    for prop,val in (('fog_density',0.008),('fog_height_falloff',0.22),('enable_volumetric_fog',True),
                     ('volumetric_fog_scattering_distribution',0.35),('volumetric_fog_distance',6500.0)):
        fc.set_editor_property(prop,val)
    h._finish(fog,'LM_Atmosphere','Lighting','Fog')
    # Saved reference camera makes the principal composition easy to revisit.
    cam=eas.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(-1120,0,310),unreal.Rotator(pitch=-2,yaw=0,roll=0))
    cam.get_component_by_class(unreal.CameraComponent).set_field_of_view(74.0)
    h._finish(cam,'LM_Camera_Reference','Cameras','Camera')
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        unreal.Vector(-1120,0,310),unreal.Rotator(pitch=-2,yaw=0,roll=0))
    h._log('reference polish complete: practical flames, flowing water, materials, fog and camera')
