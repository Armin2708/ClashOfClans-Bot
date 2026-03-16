"""Download all troop/spell/hero/pet icons from coc.guide.

Saves to templates/icons/<id>.png
Run from project root:  python scripts/download_icons.py
"""

import os
import sys
import urllib.request

# coc.guide base URL
BASE = "https://coc.guide/static/imgs"

# Manual mapping: our troop ID -> coc.guide image path
# Built by scraping all available images from the site
_URL_MAP = {
    # ── Elixir Troops ──
    "barbarian":         f"{BASE}/troop/barbarian.png",
    "archer":            f"{BASE}/troop/archer.png",
    "giant":             f"{BASE}/troop/giant.png",
    "goblin":            f"{BASE}/troop/goblin.png",
    "wall_breaker":      f"{BASE}/troop/wall-breaker.png",
    "balloon":           f"{BASE}/troop/balloon.png",
    "wizard":            f"{BASE}/troop/wizard.png",
    "healer":            f"{BASE}/troop/healer.png",
    "dragon":            f"{BASE}/troop/dragon.png",
    "pekka":             f"{BASE}/troop/pekka.png",
    "baby_dragon":       f"{BASE}/troop/babydragon.png",
    "miner":             f"{BASE}/troop/miner.png",
    "electro_dragon":    f"{BASE}/troop/electro-dragon.png",
    "yeti":              f"{BASE}/troop/yeti.png",
    "dragon_rider":      f"{BASE}/troop/dragon-rider.png",
    "electro_titan":     f"{BASE}/troop/electro-titan.png",
    "root_rider":        f"{BASE}/troop/root-rider.png",
    "thrower":           f"{BASE}/troop/thrower.png",
    "meteor_golem":      f"{BASE}/troop/grave-golem.png",  # closest available

    # ── Dark Elixir Troops ──
    "minion":            f"{BASE}/troop/gargoyle.png",       # minion = gargoyle internally
    "hog_rider":         f"{BASE}/troop/hog-rider.png",
    "valkyrie":          f"{BASE}/troop/elitevalkyrie.png",  # use valkyrie variant
    "golem":             f"{BASE}/troop/golem.png",
    "witch":             f"{BASE}/troop/dark-witch.png",
    "lava_hound":        f"{BASE}/troop/lavaloon.png",       # lava hound variant
    "bowler":            f"{BASE}/troop/bowler.png",
    "ice_golem":         f"{BASE}/troop/ice-golem.png",
    "headhunter":        f"{BASE}/troop/headhunter.png",
    "apprentice_warden": f"{BASE}/troop/apprentice-warden.png",
    "druid":             f"{BASE}/troop/druid_healer.png",
    "furnace":           f"{BASE}/troop/warlock.png",        # closest available

    # ── Siege Machines ──
    "wall_wrecker":      f"{BASE}/troop/siege-machine-ram.png",
    "battle_blimp":      f"{BASE}/troop/siege-machine-flyer.png",
    "stone_slammer":     f"{BASE}/troop/siege-bowler-balloon.png",
    "siege_barracks":    f"{BASE}/troop/battleram.png",
    "log_launcher":      f"{BASE}/troop/siege-log-launcher.png",
    "flame_flinger":     f"{BASE}/troop/siege-catapult.png",
    "troop_launcher":    f"{BASE}/troop/siege-machine-carrier.png",
    "battle_drill":      f"{BASE}/troop/battle-drill.png",

    # ── Heroes ──
    "barbarian_king":    f"{BASE}/troop/elitebarbarian.png",  # king-like barbarian
    "archer_queen":      f"{BASE}/troop/elitearcher.png",     # queen-like archer
    "grand_warden":      f"{BASE}/troop/apprentice-warden.png",
    "royal_champion":    f"{BASE}/troop/warrior-girl.png",
    "minion_prince":     f"{BASE}/troop/gargoyle.png",
    "dragon_duke":       f"{BASE}/troop/infernodragon.png",

    # ── Hero Pets ──
    "lassi":             f"{BASE}/troop/courier.png",
    "electro_owl":       f"{BASE}/troop/firecracker.png",
    "mighty_yak":        f"{BASE}/troop/boar-rider.png",
    "unicorn":           f"{BASE}/troop/healer.png",
    "frosty":            f"{BASE}/pet/frosty-10.png",
    "diggy":             f"{BASE}/pet/diggy-10.png",
    "poison_lizard":     f"{BASE}/pet/poison-lizard-10.png",
    "phoenix":           f"{BASE}/pet/phoenix-10.png",
    "spirit_fox":        f"{BASE}/troop/cookie.png",
    "angry_jelly":       f"{BASE}/pet/angry-jelly-10.png",
    "sneezy":            f"{BASE}/troop/snake-barrel.png",
    "greedy_raven":      f"{BASE}/troop/skeleton-barrel.png",

    # ── Elixir Spells ──
    "lightning_spell":    f"{BASE}/spell/lighningstorm.png",
    "healing_spell":      f"{BASE}/spell/healingwave.png",
    "rage_spell":         f"{BASE}/spell/speedup.png",
    "jump_spell":         f"{BASE}/spell/jump.png",
    "freeze_spell":       f"{BASE}/spell/freeze.png",
    "clone_spell":        f"{BASE}/spell/duplicate.png",
    "invisibility_spell": f"{BASE}/spell/invisibility.png",
    "recall_spell":       f"{BASE}/spell/recall.png",
    "revive_spell":       f"{BASE}/spell/revive.png",
    "totem_spell":        f"{BASE}/spell/bagoffrostmites.png",

    # ── Dark Spells ──
    "poison_spell":      f"{BASE}/spell/poison.png",
    "earthquake_spell":  f"{BASE}/spell/earthquake.png",
    "haste_spell":       f"{BASE}/spell/haste.png",
    "skeleton_spell":    f"{BASE}/spell/spawnskele.png",
    "bat_spell":         f"{BASE}/spell/spawnbats.png",
    "overgrowth_spell":  f"{BASE}/spell/overgrowth.png",
    "ice_block_spell":   f"{BASE}/spell/freeze.png",  # closest
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "templates", "icons")


def download_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total = len(_URL_MAP)
    downloaded = 0
    skipped = 0
    failed = 0

    for i, (tid, url) in enumerate(sorted(_URL_MAP.items()), 1):
        out_path = os.path.join(OUTPUT_DIR, f"{tid}.png")

        if os.path.exists(out_path):
            skipped += 1
            print(f"  [{i}/{total}] {tid} — exists, skipping")
            continue

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "COCBot/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()

            with open(out_path, "wb") as f:
                f.write(data)

            downloaded += 1
            print(f"  [{i}/{total}] {tid} — {len(data)/1024:.0f} KB")

        except Exception as e:
            failed += 1
            print(f"  [{i}/{total}] {tid} — FAILED: {e}")

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    print(f"Icons: {OUTPUT_DIR}")


if __name__ == "__main__":
    print(f"Downloading {len(_URL_MAP)} icons from coc.guide...\n")
    download_all()
