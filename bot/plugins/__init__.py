# These are ordered plugins and they will be executed on startup (if enabled)
# in the order that they are imported. Take care with modifying this as the
# runtime loop may work better when ordering is done efficiently.
from bot.plugins.check_game_state.check_game_state import *
from bot.plugins.fight_boss.fight_boss import *
from bot.plugins.eggs.eggs import *
from bot.plugins.level_master.level_master import *
from bot.plugins.prestige.prestige_handle_daily_limit import *
from bot.plugins.level_skills.level_skills import *
from bot.plugins.activate_skills.configure_skills import *
from bot.plugins.activate_skills.activate_skills import *
from bot.plugins.inbox.inbox import *
from bot.plugins.tapping.tapping import *
from bot.plugins.daily_rewards.daily_rewards import *
from bot.plugins.achievements.achievements import *
from bot.plugins.level_heroes.level_heroes_quick import *
from bot.plugins.level_heroes.level_heroes import *
from bot.plugins.shop_pets.shop_pets import *
from bot.plugins.shop_video_chest.shop_video_chest import *
from bot.plugins.perks.perks import *

# These plugins aren't executed on startup.
# Ordering is less important here.
from bot.plugins.prestige.prestige import *
from bot.plugins.prestige.prestige_close_to_max import *
