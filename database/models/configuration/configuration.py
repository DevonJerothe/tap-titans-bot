from peewee import (
    CharField,
    TextField,
    BooleanField,
    IntegerField,
)

from database.database import (
    BaseModel,
)

import copy


def get_default_instance_name():
    """Attempt to generate a default instance name based on the existing instances currently
    in the system.
    """
    # The count is used to determine if we need to add
    # an additional "index" or if we can just use "1".
    count = Configuration.select().count()
    # "Bot Instance " prepended to our default name through count.
    return "Tap Titans Bot Configuration %(count)s" % {
        "count": str(count + 1) if count else "1"
    }


class Configuration(BaseModel):
    grouped_fields = {
        "Generic": [
            "name",
        ],
        "Game State": [
            "abyssal",
        ],
        "Tapping": [
            "tapping_enabled",
            "tapping_interval",
        ],
        "Level Master": [
            "level_master_enabled",
            "level_master_on_start",
            "level_master_interval",
            "level_master_once_per_prestige",
        ],
        "Level Skills": [
            "level_skills_enabled",
            "level_skills_on_start",
            "level_skills_interval",
            "level_skills_heavenly_strike_amount",
            "level_skills_deadly_strike_amount",
            "level_skills_hand_of_midas_amount",
            "level_skills_fire_sword_amount",
            "level_skills_war_cry_amount",
            "level_skills_shadow_clone_amount"
        ],
        "Activate Skills": [
            "activate_skills_enabled",
            "activate_skills_on_start",
            "activate_skills_heavenly_strike",
            "activate_skills_deadly_strike",
            "activate_skills_hand_of_midas",
            "activate_skills_fire_sword",
            "activate_skills_war_cry",
            "activate_skills_shadow_clone",
        ],
        "Level Heroes": [
            "level_heroes_enabled",
            "level_heroes_skip_if_autobuy_enabled",
            "level_heroes_on_start",
            "level_heroes_interval",
            "level_heroes_quick_enabled",
            "level_heroes_quick_interval",
            "level_heroes_quick_loops",
            "level_heroes_masteries_unlocked",
        ],
        "Shop": [
            "shop_pets_purchase_enabled",
            "shop_pets_purchase_on_start",
            "shop_pets_purchase_interval",
            "shop_pets_purchase_pets",
            "shop_video_chest_enabled",
            "shop_video_chest_on_start",
            "shop_video_chest_interval",
        ],
        "Perks": [
            "perks_enabled",
            "perks_on_start",
            "perks_interval",
            "perks_spend_diamonds",
            "perks_mega_boost",
            "perks_power_of_swiping",
            "perks_adrenaline_rush",
            "perks_make_it_rain",
            "perks_mana_potion",
            "perks_doom",
            "perks_clan_crate",
        ],
        "Headgear Swap": [
            "headgear_swap_enabled",
            "headgear_swap_check_hero_index",
        ],
        "Tournaments": [
            "tournaments_enabled",
        ],
        "Automatic Prestige": [
            "prestige_time_enabled",
            "prestige_time_interval",
            "prestige_close_to_max_enabled",
            "prestige_close_to_max_fight_boss_enabled",
            "prestige_wait_when_ready_interval",
        ],
        "Artifacts": [
            "artifacts_enabled",
            "artifacts_enchantment_enabled",
            "artifacts_discovery_enabled",
            "artifacts_discovery_upgrade_enabled",
            "artifacts_discovery_upgrade_multiplier",
            "artifacts_upgrade_enabled",
            "artifacts_upgrade_artifacts",
            "artifacts_shuffle_enabled",
        ],
    }

    level_skills_choices = [
        "disable",
        "5",
        "10",
        "15",
        "20",
        "25",
        "30",
        "max",
    ]

    # Generic.
    name = CharField(
        default=get_default_instance_name,
        verbose_name="Name",
        help_text=(
            "Specify the name of this configuration."
        ),
    )
    # Game State.
    abyssal = BooleanField(
        default=False,
        verbose_name="Abyssal",
        help_text=(
            "Enable/disable the functionality that modifies certain in game functions to work while you're inside of an\n"
            "abyssal tournament. This will modify the behaviour of certain functions that may work differently or use different\n"
            "icons when inside of an abyssal tournament."
        ),
    )
    # Tapping.
    tapping_enabled = BooleanField(
        default=True,
        verbose_name="Tapping Enabled",
        help_text=(
            "Enable/disable the functionality that controls tapping on the screen in game to collect fairies and\n"
            "activate skill mini-games."
        ),
    )
    tapping_interval = IntegerField(
        default=1,
        verbose_name="Tapping Interval",
        help_text=(
            "Specify how long (in seconds) between each tapping execution."
        ),
    )
    # Level Master.
    level_master_enabled = BooleanField(
        default=True,
        verbose_name="Level Master Enabled",
        help_text=(
            "Enable/disable the functionality that controls the levelling of the sword master in game."
        ),
    )
    level_master_on_start = BooleanField(
        default=True,
        verbose_name="Level Master On Start",
        help_text=(
            "Enable/disable the functionality that controls levelling the sword master in game once\n"
            "on session startup."
        )
    )
    level_master_interval = IntegerField(
        default=45,
        verbose_name="Level Master Interval",
        help_text=(
            "Specify how long (in seconds) between each level master execution."
        ),
    )
    level_master_once_per_prestige = BooleanField(
        default=False,
        verbose_name="Level Master Once Per Prestige",
        help_text=(
            "Enable/disable the functionality that controls levelling the sword master once per prestige.\n"
            "This is useful if you're far along in the game and only require levelling the sword master\n"
            "very infrequently per prestige."
        ),
    )
    # Level Skills.
    level_skills_enabled = BooleanField(
        default=True,
        verbose_name="Level Skills Enabled",
        help_text=(
            "Enable/disable the functionality that controls levelling skills in game."
        ),
    )
    level_skills_on_start = BooleanField(
        default=True,
        verbose_name="Level Skills On Start",
        help_text=(
            "Enable/disable the functionality that controls levelling skills once on session startup."
        ),
    )
    level_skills_interval = IntegerField(
        default=300,
        verbose_name="Level Skills Interval",
        help_text=(
            "Specify how long (in seconds) between each level skills execution."
        ),
    )
    level_skills_heavenly_strike_amount = CharField(
        default="max",
        choices=level_skills_choices,
        verbose_name="Level Skills Heavenly Strike Amount",
        help_text=(
            "Specify the amount to level the \"heavenly strike\" skill in game. Setting this to \"max\"\n"
            "will attempt to level the skill to the max level available. Setting this to \"disable\" will\n"
            "not level the skill in game at all."
        ),
    )
    level_skills_deadly_strike_amount = CharField(
        default="max",
        choices=level_skills_choices,
        verbose_name="Level Skills Deadly Strike Amount",
        help_text=(
            "Specify the amount to level the \"deadly strike\" skill in game. Setting this to \"max\"\n"
            "will attempt to level the skill to the max level available. Setting this to \"disable\" will\n"
            "not level the skill in game at all."
        ),
    )
    level_skills_hand_of_midas_amount = CharField(
        default="max",
        choices=level_skills_choices,
        verbose_name="Level Skills Hand Of Midas Amount",
        help_text=(
            "Specify the amount to level the \"hand of midas\" skill in game. Setting this to \"max\"\n"
            "will attempt to level the skill to the max level available. Setting this to \"disable\" will\n"
            "not level the skill in game at all."
        ),
    )
    level_skills_fire_sword_amount = CharField(
        default="max",
        choices=level_skills_choices,
        verbose_name="Level Skills Fire Sword Amount",
        help_text=(
            "Specify the amount to level the \"fire sword\" skill in game. Setting this to \"max\"\n"
            "will attempt to level the skill to the max level available. Setting this to \"disable\" will\n"
            "not level the skill in game at all."
        ),
    )
    level_skills_war_cry_amount = CharField(
        default="max",
        choices=level_skills_choices,
        verbose_name="Level Skills War Cry Amount",
        help_text=(
            "Specify the amount to level the \"war cry\" skill in game. Setting this to \"max\"\n"
            "will attempt to level the skill to the max level available. Setting this to \"disable\" will\n"
            "not level the skill in game at all."
        ),
    )
    level_skills_shadow_clone_amount = CharField(
        default="max",
        choices=level_skills_choices,
        verbose_name="Level Skills Shadow Clone Amount",
        help_text=(
            "Specify the amount to level the \"shadow clone\" skill in game. Setting this to \"max\"\n"
            "will attempt to level the skill to the max level available. Setting this to \"disable\" will\n"
            "not level the skill in game at all."
        ),
    )
    # Activate Skills.
    activate_skills_enabled = BooleanField(
        default=True,
        verbose_name="Activate Skills Enabled",
        help_text=(
            "Enable/disable the functionality that controls activating skills in game."
        ),
    )
    activate_skills_on_start = BooleanField(
        default=True,
        verbose_name="Activate Skills On Start",
        help_text=(
            "Enable/disable the functionality that controls activating skills once on session startup."
        ),
    )
    activate_skills_interval = IntegerField(
        default=2,
        verbose_name="Activate Skills Interval",
        help_text=(
            "Specify how long (in seconds) between each activate skills execution, this is only used to control\n"
            "how often skills are checked to see if they're ready to be activated."
        ),
    )
    activate_skills_heavenly_strike = CharField(
        default="0/off/0/0",
        verbose_name="Activate Skills Heavenly Strike",
        help_text=(
            "Determine how the \"heavenly strike\" skill is activated in game. Use the following format to\n"
            "set the skills weight, enabled state, interval and clicks: \"(weight)/(on/off)/(interval)/(clicks)\"."
        ),
    )
    activate_skills_deadly_strike = CharField(
        default="0/off/0/0",
        verbose_name="Activate Skills Deadly Strike",
        help_text=(
            "Determine how the \"deadly strike\" skill is activated in game. Use the following format to\n"
            "set the skills weight, enabled state, interval and clicks: \"(weight)/(on/off)/(interval)/(clicks)\"."
        ),
    )
    activate_skills_hand_of_midas = CharField(
        default="0/off/0/0",
        verbose_name="Activate Skills Hand Of Midas",
        help_text=(
            "Determine how the \"hand of midas\" skill is activated in game. Use the following format to\n"
            "set the skills weight, enabled state, interval and clicks: \"(weight)/(on/off)/(interval)/(clicks)\"."
        ),
    )
    activate_skills_fire_sword = CharField(
        default="0/off/0/0",
        verbose_name="Activate Skills Fire Sword",
        help_text=(
            "Determine how the \"fire sword\" skill is activated in game. Use the following format to\n"
            "set the skills weight, enabled state, interval and clicks: \"(weight)/(on/off)/(interval)/(clicks)\"."
        ),
    )
    activate_skills_war_cry = CharField(
        default="0/off/0/0",
        verbose_name="Activate Skills War Cry",
        help_text=(
            "Determine how the \"war cry\" skill is activated in game. Use the following format to\n"
            "set the skills weight, enabled state, interval and clicks: \"(weight)/(on/off)/(interval)/(clicks)\"."
        ),
    )
    activate_skills_shadow_clone = CharField(
        default="0/off/0/0",
        verbose_name="Activate Skills Shadow Clone",
        help_text=(
            "Determine how the \"shadow clone\" skill is activated in game. Use the following format to\n"
            "set the skills weight, enabled state, interval and clicks: \"(weight)/(on/off)/(interval)/(clicks)\"."
        ),
    )
    # Level Heroes.
    level_heroes_enabled = BooleanField(
        default=True,
        verbose_name="Level Heroes Enabled",
        help_text=(
            "Enable/disable the functionality that controls levelling heroes in game."
        ),
    )
    level_heroes_skip_if_autobuy_enabled = BooleanField(
        default=True,
        verbose_name="Level Heroes Skip If Autobuy Enabled",
        help_text=(
            "Enable/disable the functionality that controls skipping manual hero levelling when the\n"
            "autobuy feature is currently enabled in game."
        ),
    )
    level_heroes_on_start = BooleanField(
        default=True,
        verbose_name="Level Heroes On Start",
        help_text=(
            "Enable/disable the functionality that controls levelling heroes once on session startup."
        ),
    )
    level_heroes_interval = IntegerField(
        default=30,
        verbose_name="Level Heroes Interval",
        help_text=(
            "Specify how long (in seconds) between each level heroes execution."
        ),
    )
    level_heroes_quick_enabled = BooleanField(
        default=True,
        verbose_name="Level Heroes Quick Enabled",
        help_text=(
            "Enable/disable the functionality that controls levelling heroes quickly in game.\n"
            "Quick hero levelling works similarly to the normal hero levelling function, except\n"
            "no drags are performed to travel to the first max level hero in game, or the bottom\n"
            "of the heroes panel."
        ),
    )
    level_heroes_quick_on_start = BooleanField(
        default=True,
        verbose_name="Level Heroes Quick Enabled",
        help_text=(
            "Enable/disable the functionality that controls levelling heroes quickly in game\n"
            "once on session startup."
        ),
    )
    level_heroes_quick_interval = IntegerField(
        default=20,
        verbose_name="Level Heroes Quick Interval",
        help_text=(
            "Specify how long (in seconds) between each level heroes quick execution."
        ),
    )
    level_heroes_quick_loops = IntegerField(
        default=1,
        verbose_name="Level Heroes Quick Loops",
        help_text=(
            "Specify how many times the quick hero levelling functionality is performed per execution,\n"
            "one loop will level each hero on the screen once, increasing the number of loops may improve\n"
            "your hero levelling efficiency."
        ),
    )
    level_heroes_masteries_unlocked = BooleanField(
        default=False,
        verbose_name="Level Heroes Masteries Unlocked",
        help_text=(
            "Enable/disable the functionality that controls whether or not to level each hero once\n"
            "when levelling heroes in game. This will speed up the levelling process substantially\n"
            "if all of your heroes have at least one mastery."
        ),
    )
    # Shop.
    shop_pets_purchase_enabled = BooleanField(
        default=False,
        verbose_name="Shop Pet Purchase Enabled",
        help_text=(
            "Enable/disable the functionality that controls purchasing pets from the shop in game."
        ),
    )
    shop_pets_purchase_on_start = BooleanField(
        default=False,
        verbose_name="Shop Pet Purchase On Start",
        help_text=(
            "Enable/disable the functionality that controls purchasing pets from the shop in game once\n"
            "on session startup."
        ),
    )
    shop_pets_purchase_interval = IntegerField(
        default=10800,
        verbose_name="Shop Pet Purchase Interval",
        help_text=(
            "Specify how long (in seconds) between each pets purchase execution."
        ),
    )
    shop_pets_purchase_pets = TextField(
        default="",
        verbose_name="Shop Pet Purchase Pets",
        help_text=(
            "Specify a comma-separated list of in game pets to search for when attempting to purchase\n"
            "pets from the in game shop. Example: \"fluffers,kit,percy\"."
        ),
    )
    shop_video_chest_enabled = BooleanField(
        default=False,
        verbose_name="Shop Video Chest Enabled",
        help_text=(
            "Enable/disable the functionality that controls the collection of the video chest from the\n"
            "shop in game."
        ),
    )
    shop_video_chest_on_start = BooleanField(
        default=False,
        verbose_name="Shop Video Chest On Start",
        help_text=(
            "Enable/disable the functionality that controls the collection of the video chest from the\n"
            "shop in game once on session startup."
        ),
    )
    shop_video_chest_interval = IntegerField(
        default=10800,
        verbose_name="Shop Video Chest Interval",
        help_text=(
            "Specify how long (in seconds) between each video chest execution."
        ),
    )
    # Perks.
    perks_enabled = BooleanField(
        default=False,
        verbose_name="Perks Enabled",
        help_text=(
            "Enable/disable the functionality that controls buying and using perks in game."
        ),
    )
    perks_on_start = BooleanField(
        default=False,
        verbose_name="Perks On Start",
        help_text=(
            "Enable/disable the functionality that controls buying and using perks in game\n"
            "once on session startup."
        ),
    )
    perks_interval = IntegerField(
        default=3600,
        verbose_name="Perks Interval",
        help_text=(
            "Specify how long (in seconds) between each perks execution."
        ),
    )
    perks_spend_diamonds = BooleanField(
        default=False,
        verbose_name="Perks Spend Diamonds",
        help_text=(
            "Enable/disable the functionality that controls buying perks in game with diamonds,\n"
            "this requires your account to have enough diamonds available to buy perks."
        ),
    )
    perks_mega_boost = CharField(
        default="off/1",
        verbose_name="Perks Mega Boost",
        help_text=(
            "Determine how the \"mega boost\" perk is used in game. Use the following format to\n"
            "set the perks enabled state and tier: \"(on/off)/(int)\"."
        ),
    )
    perks_power_of_swiping = CharField(
        default="off/1",
        verbose_name="Perks Power Of Swiping",
        help_text=(
            "Determine how the \"power of swiping\" perk is used in game. Use the following format to\n"
            "set the perks enabled state and tier: \"(on/off)/(int)\"."
        ),
    )
    perks_adrenaline_rush = CharField(
        default="off/1",
        verbose_name="Perks Adrenaline Rush",
        help_text=(
            "Determine how the \"adrenaline rush\" perk is used in game. Use the following format to\n"
            "set the perks enabled state and tier: \"(on/off)/(int)\"."
        ),
    )
    perks_make_it_rain = CharField(
        default="off/1",
        verbose_name="Perks Make It Rain",
        help_text=(
            "Determine how the \"make it rain\" perk is used in game. Use the following format to\n"
            "set the perks enabled state and tier: \"(on/off)/(int)\"."
        ),
    )
    perks_mana_potion = CharField(
        default="off/1",
        verbose_name="Perks Mana Potion",
        help_text=(
            "Determine how the \"mana potion\" perk is used in game. Use the following format to\n"
            "set the perks enabled state and tier: \"(on/off)/(int)\"."
        ),
    )
    perks_doom = CharField(
        default="off/1",
        verbose_name="Perks Doom",
        help_text=(
            "Determine how the \"doom\" perk is used in game. Use the following format to\n"
            "set the perks enabled state and tier: \"(on/off)/(int)\"."
        ),
    )
    perks_clan_crate = CharField(
        default="off",
        verbose_name="Perks Clan Crate",
        help_text=(
            "Determine how the \"clan crate\" perk is used in game. Use the following format to\n"
            "set the perks enabled state: \"(on/off)\"."
        ),
    )
    # Headgear Swap.
    headgear_swap_enabled = BooleanField(
        default=False,
        verbose_name="Headgear Swap Enabled",
        help_text=(
            "Enable/disable the functionality that controls headgear swapping in game based on the most\n"
            "powerful hero currently in game. This functionality requires you to have locked pieces of headgear\n"
            "that contain the proper damage type boost: (\"warrior\", \"ranger\", \"mage\"). If enabled, this function\n"
            "runs every time the hero levelling process is finished. Headgear is only swapped when the most\n"
            "powerful hero has changed from the last check in game."
        ),
    )
    headgear_swap_check_hero_index = IntegerField(
        default=3,
        verbose_name="Headgear Swap Check Hero Index",
        help_text=(
            "Specify which hero to look at when parsing the most powerful hero from the game, the default here is usually\n"
            "fine, but depending on how far along in the game you are, sometimes different hero indexes offer a bigger damage\n"
            "boost in game."
        ),
    )
    # Tournaments.
    tournaments_enabled = BooleanField(
        default=True,
        verbose_name="Tournaments Enabled",
        help_text=(
            "Enable/disable the functionality that controls tournament participation and rewards collection in game.\n"
            "Note: All tournament functionality is handled when a prestige takes place in game."
        ),
    )
    # Automatic Prestige.
    prestige_time_enabled = BooleanField(
        default=True,
        verbose_name="Prestige Time Enabled",
        help_text=(
            "Enable/disable the functionality that controls automatic prestige based on a time interval."
        ),
    )
    prestige_time_interval = IntegerField(
        default=2700,
        verbose_name="Prestige Time Interval",
        help_text=(
            "Specify how long (in secondS) between each timed prestige execution in game."
        ),
    )
    prestige_close_to_max_enabled = BooleanField(
        default=False,
        verbose_name="Prestige Close To Max Enabled",
        help_text=(
            "Enable/disable the functionality that controls automatic prestige based on when you're \"close\" to\n"
            "your max stage in game. This is handled in two ways, if an event is running in game, the \"Prestige\" icon "
            "on the master panel is checked for the current event icon, otherwise the skill tree is opened and the\n"
            "\"Prestige To Reset\" is searched for."
        ),
    )
    prestige_close_to_max_fight_boss_enabled = BooleanField(
        default=False,
        verbose_name="Prestige Close To Max Fight Boss Enabled",
        help_text=(
            "Enable/disable the functionality that controls automatic prestige based on when you're \"close\" to\n"
            "your max stage (see \"Prestige Close To Max Enabled\" above) and the fight boss icon appears for the first\n"
            "time after the close to max threshold is reached. This setting may or may not be more efficient for you\n"
            "depending on your maximum stage and current end game status. Note: The \"Prestige Wait When Ready Interval\"\n"
            "is ignored when this is enabled, instead, as soon as the fight boss icon appears, a prestige is performed."
        ),
    )
    prestige_wait_when_ready_interval = IntegerField(
        default=0,
        verbose_name="Prestige Wait When Ready Interval",
        help_text=(
            "Specify how long (in secondS) to wait once a prestige is ready (based on the above toggles) before the\n"
            "prestige is actually performed."
        ),
    )
    # Artifacts.
    artifacts_enabled = BooleanField(
        default=True,
        verbose_name="Artifacts Enabled",
        help_text=(
            "Enable/disable the functionality that controls artifact enchantment/discovery/upgrades after a\n"
            "prestige is performed."
        ),
    )
    artifacts_enchantment_enabled = BooleanField(
        default=True,
        verbose_name="Artifacts Enchantment Enabled",
        help_text=(
            "Enable/disable the functionality that controls artifact enchantment in game."
        ),
    )
    artifacts_discovery_enabled = BooleanField(
        default=True,
        verbose_name="Artifacts Discovery Enabled",
        help_text=(
            "Enable/disable the functionality that controls artifact discovery in game."
        ),
    )
    artifacts_discovery_upgrade_enabled = BooleanField(
        default=False,
        verbose_name="Artifacts Discovery Upgrade Enabled",
        help_text=(
            "Enable/disable the functionality that controls upgrading artifacts after discovering\n"
            "one in game."
        ),
    )
    artifacts_discovery_upgrade_multiplier = CharField(
        default="max",
        verbose_name="Artifact Discovery Upgrade Multiplier",
        help_text=(
            "Specify the in game upgrade multiplier used when upgrading a newly discovered artifact\n"
            "in game. Choose one of: \"max\", \"25\", \"5\", \"1\"."
        ),
    )
    artifacts_upgrade_enabled = BooleanField(
        default=True,
        verbose_name="Artifacts Upgrade Enabled",
        help_text=(
            "Enable/disable the functionality that controls upgrading selected artifacts after a prestige\n"
            "is performed in game."
        ),
    )
    artifacts_upgrade_artifacts = TextField(
        default="book_of_shadows",
        verbose_name="Artifacts Upgrade Artifacts",
        help_text=(
            "Specify a comma-separated list of in game artifacts to upgrade after a prestige is performed\n"
            "in game. Example: \"book_of_shadows,stone_of_the_valrunes,heroic_shield\"."
        ),
    )
    artifacts_shuffle_enabled = BooleanField(
        default=False,
        verbose_name="Artifacts Shuffle Enabled",
        help_text=(
            "Enable/disable the functionality that controls shuffling of artifacts specified in the comma-separated\n"
            "list above. This will also shuffle the list of artifacts to upgrade on every subsequent prestige."
        ),
    )

    def generate_defaults(self):
        """Generate the default configurations if they do not currently exist.
        """
        if self.select().count() == 0:
            self.create()

    def prep_field(self, value, delimiter, append=None, coerce_value=None, coerce_index=None):
        """
        """
        if not value:
            return value

        value = value.replace(" ", "").replace("\n", "")
        value = value.split(delimiter)

        if value:
            if coerce_value:
                for index, val in enumerate(value):
                    if val in coerce_value:
                        value[index] = coerce_value[val]
            if coerce_index:
                for index, val in enumerate(value):
                    if index in coerce_index:
                        value[index] = coerce_index[index](value[index])
            if append:
                if isinstance(append, list):
                    for val in append:
                        value.append(val)
                else:
                    value.append(append)

        return value

    def prep_comma_separated_list(self, value):
        """Prep a simple comma separated list of strings.
        """
        return self.prep_field(
            value=value,
            delimiter=",",
        )

    def prep_perk_list(self, value, append=None):
        """Prep the more complex perk field, which is required to have two indexes, the first one being an "enabled"
        toggle, and the second one being a "tier" to set the perk to when activated.
        """
        return self.prep_field(
            value=value,
            delimiter="/",
            append=append,
            coerce_value={
                "on": True,
                "off": False,
            },
            coerce_index={
                1: int,
            },
        )

    def prep_skill_list(self, value, append=None):
        """Prep the more complex skill field, which is required to have four indexes, the first one being the "weight"
        of the skill, second being the "enabled" toggle, third being the "interval", and the fourth being the "clicks".
        """
        return self.prep_field(
            value=value,
            delimiter="/",
            append=append,
            coerce_value={
                "on": True,
                "off": False,
            },
            coerce_index={
                0: int,
                2: int,
                3: int,
            },
        )

    def prep(self):
        """Prep the configuration, dealing with any value modifications to make the configuration instance more consumable by
        a bot instance.
        """
        obj = copy.deepcopy(self)

        obj.shop_pets_purchase_pets = self.prep_comma_separated_list(value=self.shop_pets_purchase_pets)
        obj.artifacts_upgrade_artifacts = self.prep_comma_separated_list(value=self.artifacts_upgrade_artifacts)

        # Skills.
        obj.activate_skills_heavenly_strike = self.prep_skill_list(self.activate_skills_heavenly_strike, append="heavenly_strike")
        obj.activate_skills_deadly_strike = self.prep_skill_list(self.activate_skills_deadly_strike, append="deadly_strike")
        obj.activate_skills_hand_of_midas = self.prep_skill_list(self.activate_skills_hand_of_midas, append="hand_of_midas")
        obj.activate_skills_fire_sword = self.prep_skill_list(self.activate_skills_fire_sword, append="fire_sword")
        obj.activate_skills_war_cry = self.prep_skill_list(self.activate_skills_war_cry, append="war_cry")
        obj.activate_skills_shadow_clone = self.prep_skill_list(self.activate_skills_shadow_clone, append="shadow_clone")

        # Perks.
        obj.perks_mega_boost = self.prep_perk_list(self.perks_mega_boost, append="mega_boost")
        obj.perks_power_of_swiping = self.prep_perk_list(self.perks_power_of_swiping, append="power_of_swiping")
        obj.perks_adrenaline_rush = self.prep_perk_list(self.perks_adrenaline_rush, append="adrenaline_rush")
        obj.perks_make_it_rain = self.prep_perk_list(self.perks_make_it_rain, append="make_it_rain")
        obj.perks_mana_potion = self.prep_perk_list(self.perks_mana_potion, append="mana_potion")
        obj.perks_doom = self.prep_perk_list(self.perks_doom, append="doom")
        # Clan crate perk doesn't support a "tiered" approach.
        # We'll explicitly set the tier to "0" .
        obj.perks_clan_crate = self.prep_perk_list(self.perks_clan_crate, append=[0, "clan_crate"])

        return obj
