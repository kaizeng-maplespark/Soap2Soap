"""Soap2Soap V2 — Main Pipeline Orchestrator."""
from __future__ import annotations
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v2.core.schema import PipelineState
from v2.pipeline import step0_transcribe, step1_analyze, step2_characters, step3_compile, step3b_camera_groups, step4_keyframes, step4b_inspect, step5_video, step6_merge

_step_t0 = 0.0
_pipeline_t0 = 0.0

def _step_start(step_num, name):
    global _step_t0
    _step_t0 = time.time(); elapsed = time.time() - _pipeline_t0
    print(f"\n{'─'*60}\n▶  Step {step_num}: {name}  [pipeline +{elapsed:.0f}s]\n{'─'*60}")
def _step_done(): print(f"✔  done in {time.time()-_step_t0:.1f}s")

def run_pipeline(video_path, style="disney", max_shots=10, dev_mode=True, output_dir=".", use_whisper=True,
                 generation_mode="consistency", yes=False, no_inspect=False, video_model="seeddance",
                 dialogue_lang="auto", keyframe_model="gemini", source_frame_grid=False,
                 finishing_strength="balanced"):
    global _pipeline_t0
    _pipeline_t0 = time.time()
    print("\n" + "="*70 + "\n🎬 Soap2Soap V2 — Video-to-Video Pipeline\n" + "="*70)
    print(f"  Input    : {video_path}\n  Style    : {style}")
    if style == "cinefilter": print(f"  Finish   : {finishing_strength}")
    print(f"  Max shots: {max_shots}\n  Mode     : {generation_mode}\n  Video    : {'static 3s fallback (dev mode)' if dev_mode else video_model.upper()}\n  Whisper  : {'enabled' if use_whisper else 'disabled'}\n  Output   : {output_dir}\n" + "="*70)
    state = PipelineState(video_path=video_path, style=style, max_shots=max_shots, dev_mode=dev_mode,
        output_dir=output_dir, generation_mode=generation_mode, video_model=video_model,
        dialogue_lang=dialogue_lang, keyframe_model=keyframe_model, source_frame_grid=source_frame_grid,
        finishing_strength=finishing_strength)
    video_base=os.path.splitext(os.path.basename(video_path))[0]; video_dir=os.path.dirname(os.path.abspath(video_path)); cache_path=os.path.join(video_dir,f"{video_base}_analysis.json")
    if os.path.exists(cache_path):
        print(f"\n  ↩️  Loading cached analysis from {cache_path}"); state=_load_state(state,cache_path)
        duration=step1_analyze._get_video_duration(video_path); state.shots=step1_analyze._fix_timestamps(state.shots,duration); state.shots=step1_analyze._normalize_scene_ids(state.shots)
    else:
        transcript=""; dialogue_lines=[]
        if use_whisper:
            _step_start("0/7","Audio Transcription"); dialogue_lines=step0_transcribe.run(state); transcript=step0_transcribe.format_transcript_for_prompt(dialogue_lines); _step_done()
        _step_start("1/7","Video Analysis"); state=step1_analyze.run(state,transcript=transcript,transcript_lines=dialogue_lines,yes=yes); _save_state(state,cache_path); _step_done()
    _step_start("2/7","Character Reference Images"); state=step2_characters.run(state); _step_done()
    _step_start("3/7","Prompt Compilation + Style Rewrite"); state=step3_compile.run(state); _step_done()
    if generation_mode=="camera_tree": _step_start("3b/7","Camera Group Analysis"); state=step3b_camera_groups.run(state); _step_done()
    _step_start("4/7",f"Keyframe Generation [{generation_mode.upper()}]"); state=step4_keyframes.run(state); _step_done()
    if not no_inspect: _step_start("4b/7","Keyframe Inspection & Auto-Fix"); state=step4b_inspect.run(state); _step_done()
    _step_start("5/7","Video Generation"); state=step5_video.run(state); _step_done()
    _step_start("6/7","Video Merge"); final_video=step6_merge.run(state); _step_done()
    print("\n📊 Pipeline Summary"); print(state.to_summary()); return final_video

def _i2v_with_dialogue(shot):
    base=shot.i2v_prompt or ""
    if not shot.dialogue: return base
    note=" 台词："+"；".join(f'{d.speaker_id}说："{d.text}"' for d in shot.dialogue)+"。"
    return base if note.strip() in base else base+note

def _save_state(state,path):
    data={"video_path":state.video_path,"style":state.style,"aspect_ratio":state.aspect_ratio,
          "characters":[{"id":c.id,"name":c.name,"description":c.description} for c in state.characters],"shots":[]}
    for s in state.shots:
        data["shots"].append({"index":s.index,"scene_id":s.scene_id,"time_range":s.time_range,"start_time":s.start_time,"end_time":s.end_time,"duration":s.duration,
        "setting_description":s.setting_description,"environment_description":s.environment_description,"lighting_setup":s.lighting_setup,"color_grading":s.color_grading,
        "shot_size":s.shot_size,"camera_angle":s.camera_angle,"camera_movement":s.camera_movement,"focal_length":s.focal_length,"depth_of_field":s.depth_of_field,
        "mood_atmosphere":s.mood_atmosphere,"composition":s.composition,"subject_movement":s.subject_movement,"characters":s.characters,
        "dialogue":[{"speaker_id":d.speaker_id,"text":d.text} for d in s.dialogue],"t2i_prompt":s.t2i_prompt,"i2v_prompt":_i2v_with_dialogue(s)})
    with open(path,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)

def _load_state(state,path):
    from v2.core.schema import Character,Dialogue,Shot
    from v2.core.reference_store import ReferenceStore,ReferenceEntity
    with open(path,encoding="utf-8") as f: data=json.load(f)
    state.aspect_ratio=data.get("aspect_ratio","16:9"); store=ReferenceStore()
    for idx,c in enumerate(data.get("characters",[])):
        char=Character(id=c["id"],name=c["name"],description=c["description"]); state.characters.append(char); store.add_entity(ReferenceEntity(entity_id=char.id,entity_type="character",description=char.description,image_index=idx+1))
    state.reference_store=store
    for s in data.get("shots",[]):
        state.shots.append(Shot(index=s["index"],scene_id=s["scene_id"],time_range=s["time_range"],start_time=s["start_time"],end_time=s["end_time"],duration=s["duration"],
        setting_description=s.get("setting_description",""),environment_description=s.get("environment_description",""),lighting_setup=s.get("lighting_setup",""),color_grading=s.get("color_grading",""),shot_size=s.get("shot_size",""),camera_angle=s.get("camera_angle",""),camera_movement=s.get("camera_movement",""),focal_length=s.get("focal_length",""),depth_of_field=s.get("depth_of_field",""),mood_atmosphere=s.get("mood_atmosphere",""),composition=s.get("composition",""),subject_movement=s.get("subject_movement",""),characters=s.get("characters",[]),dialogue=[Dialogue(d["speaker_id"],d["text"]) for d in s.get("dialogue",[])],t2i_prompt=s.get("t2i_prompt",""),i2v_prompt=s.get("i2v_prompt","")))
    return state

def main():
    p=argparse.ArgumentParser(description="Soap2Soap / CineFilter video-to-video generation")
    p.add_argument("video"); p.add_argument("--style",default="disney",choices=["realistic","cinefilter","disney","pixar","anime","japanese_anime","clay","lego","family_guy"])
    p.add_argument("--finishing-strength",default="balanced",choices=["faithful","balanced","strong"],help="CineFilter transformation strength")
    p.add_argument("--shots",type=int,default=10); p.add_argument("--real-video",action="store_true"); p.add_argument("--output-dir",default="."); p.add_argument("--no-whisper",action="store_true")
    p.add_argument("--mode",default="consistency",choices=["default","consistency","camera_tree"]); p.add_argument("--yes",action="store_true"); p.add_argument("--no-inspect",action="store_true")
    p.add_argument("--video-model",default="seeddance",choices=["seeddance","veo"]); p.add_argument("--keyframe-model",default="gemini",choices=["gemini","gpt-image"]); p.add_argument("--dialogue-lang",default="auto",choices=["auto","zh","en"]); p.add_argument("--source-frame-grid",action="store_true")
    a=p.parse_args(); final=run_pipeline(a.video,a.style,a.shots,not a.real_video,a.output_dir,not a.no_whisper,a.mode,a.yes,a.no_inspect,a.video_model,a.dialogue_lang,a.keyframe_model,a.source_frame_grid,a.finishing_strength)
    if final: print(f"\n🎉 Done! Final video: {final}")
    else: sys.exit(1)
if __name__=="__main__": main()
