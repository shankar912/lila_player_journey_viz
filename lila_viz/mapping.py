from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapConfig:
    map_id: str
    scale: float
    origin_x: float
    origin_z: float
    image_filename: str
    image_size_px: int = 1024

    def world_to_pixel(self, x: float, z: float) -> tuple[float, float]:
        """
        README mapping:
          u = (x - origin_x) / scale
          v = (z - origin_z) / scale
          px = u * 1024
          py = (1 - v) * 1024   (flip Y; image origin is top-left)
        """
        u = (x - self.origin_x) / self.scale
        v = (z - self.origin_z) / self.scale
        px = u * self.image_size_px
        py = (1.0 - v) * self.image_size_px
        return px, py


MAPS: dict[str, MapConfig] = {
    "AmbroseValley": MapConfig(
        map_id="AmbroseValley",
        scale=900,
        origin_x=-370,
        origin_z=-473,
        image_filename="AmbroseValley_Minimap.png",
    ),
    "GrandRift": MapConfig(
        map_id="GrandRift",
        scale=581,
        origin_x=-290,
        origin_z=-290,
        image_filename="GrandRift_Minimap.png",
    ),
    "Lockdown": MapConfig(
        map_id="Lockdown",
        scale=1000,
        origin_x=-500,
        origin_z=-500,
        image_filename="Lockdown_Minimap.jpg",
    ),
}


def is_bot_user_id(user_id: str) -> bool:
    # README: bots use short numeric IDs; humans are UUIDs.
    return user_id.isdigit()

