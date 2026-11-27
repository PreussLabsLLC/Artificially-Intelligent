docker exec -w /data/Artificially-Intelligent santa-dev python3 agents/generate_scene_plan.py S01E05
if ($LASTEXITCODE -eq 0) {
    docker exec -w /data/Artificially-Intelligent santa-dev python3 engine/produce_episode.py S01E05
}