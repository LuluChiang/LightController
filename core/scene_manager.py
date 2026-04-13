import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SCENES_FILE = Path(__file__).parent.parent / "scenes.json"


@dataclass
class Scene:
    name: str
    red: int        # 0–255
    green: int      # 0–255
    blue: int       # 0–255
    brightness: int # 0–255


class SceneManager:
    def __init__(self, path: Path = SCENES_FILE):
        self._path = path
        self._scenes: dict[str, Scene] = {}
        self.load()

    def load(self) -> None:
        try:
            with self._path.open("r", encoding="utf-8") as f:
                raw: list[dict] = json.load(f)
            self._scenes = {item["name"]: Scene(**item) for item in raw}
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            self._scenes = {}

    def save(self) -> None:
        data = [asdict(s) for s in self._scenes.values()]
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all(self) -> list[Scene]:
        return list(self._scenes.values())

    def get(self, name: str) -> Optional[Scene]:
        return self._scenes.get(name)

    def upsert(self, scene: Scene) -> None:
        self._scenes[scene.name] = scene
        self.save()

    def delete(self, name: str) -> bool:
        if name in self._scenes:
            del self._scenes[name]
            self.save()
            return True
        return False

    def rename(self, old_name: str, new_name: str) -> bool:
        scene = self._scenes.pop(old_name, None)
        if scene is None:
            return False
        scene.name = new_name
        self._scenes[new_name] = scene
        self.save()
        return True
