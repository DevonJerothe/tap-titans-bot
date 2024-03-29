# Generated by Django 3.2.4 on 2021-07-05 12:16

import database.models.configuration
import database.models.instance
import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default=database.models.configuration.get_default_configuration_name, help_text='Specify the name of this configuration.', max_length=255, verbose_name='Name')),
                ('abyssal', models.BooleanField(default=False, help_text="Enable/disable the functionality that modifies certain in game functions to work while you're inside of an\nabyssal tournament. This will modify the behaviour of certain functions that may work differently or use different\nicons when inside of an abyssal tournament.", verbose_name='Abyssal')),
                ('tapping_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls tapping on the screen in game to collect fairies and\nactivate skill mini-games.', verbose_name='Tapping Enabled')),
                ('tapping_interval', models.IntegerField(default=1, help_text='Specify how long (in seconds) between each tapping execution.', verbose_name='Tapping Interval')),
                ('level_master_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls the levelling of the sword master in game.', verbose_name='Level Master Enabled')),
                ('level_master_on_start', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling the sword master in game once\non session startup.', verbose_name='Level Master On Start')),
                ('level_master_interval', models.IntegerField(default=45, help_text='Specify how long (in seconds) between each level master execution.', verbose_name='Level Master Interval')),
                ('level_master_once_per_prestige', models.BooleanField(default=False, help_text="Enable/disable the functionality that controls levelling the sword master once per prestige.\nThis is useful if you're far along in the game and only require levelling the sword master\nvery infrequently per prestige.", verbose_name='Level Master Once Per Prestige')),
                ('level_skills_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling skills in game.', verbose_name='Level Skills Enabled')),
                ('level_skills_on_start', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling skills once on session startup.', verbose_name='Level Skills On Start')),
                ('level_skills_interval', models.IntegerField(default=300, help_text='Specify how long (in seconds) between each level skills execution.', verbose_name='Level Skills Interval')),
                ('level_skills_heavenly_strike_amount', models.CharField(choices=[('disable', 'disable'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('max', 'max')], default='max', help_text='Specify the amount to level the "heavenly strike" skill in game. Setting this to "max"\nwill attempt to level the skill to the max level available. Setting this to "disable" will\nnot level the skill in game at all.', max_length=255, verbose_name='Level Skills Heavenly Strike Amount')),
                ('level_skills_deadly_strike_amount', models.CharField(choices=[('disable', 'disable'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('max', 'max')], default='max', help_text='Specify the amount to level the "deadly strike" skill in game. Setting this to "max"\nwill attempt to level the skill to the max level available. Setting this to "disable" will\nnot level the skill in game at all.', max_length=255, verbose_name='Level Skills Deadly Strike Amount')),
                ('level_skills_hand_of_midas_amount', models.CharField(choices=[('disable', 'disable'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('max', 'max')], default='max', help_text='Specify the amount to level the "hand of midas" skill in game. Setting this to "max"\nwill attempt to level the skill to the max level available. Setting this to "disable" will\nnot level the skill in game at all.', max_length=255, verbose_name='Level Skills Hand Of Midas Amount')),
                ('level_skills_fire_sword_amount', models.CharField(choices=[('disable', 'disable'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('max', 'max')], default='max', help_text='Specify the amount to level the "fire sword" skill in game. Setting this to "max"\nwill attempt to level the skill to the max level available. Setting this to "disable" will\nnot level the skill in game at all.', max_length=255, verbose_name='Level Skills Fire Sword Amount')),
                ('level_skills_war_cry_amount', models.CharField(choices=[('disable', 'disable'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('max', 'max')], default='max', help_text='Specify the amount to level the "war cry" skill in game. Setting this to "max"\nwill attempt to level the skill to the max level available. Setting this to "disable" will\nnot level the skill in game at all.', max_length=255, verbose_name='Level Skills War Cry Amount')),
                ('level_skills_shadow_clone_amount', models.CharField(choices=[('disable', 'disable'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30'), ('max', 'max')], default='max', help_text='Specify the amount to level the "shadow clone" skill in game. Setting this to "max"\nwill attempt to level the skill to the max level available. Setting this to "disable" will\nnot level the skill in game at all.', max_length=255, verbose_name='Level Skills Shadow Clone Amount')),
                ('activate_skills_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls activating skills in game.', verbose_name='Activate Skills Enabled')),
                ('activate_skills_on_start', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls activating skills once on session startup.', verbose_name='Activate Skills On Start')),
                ('activate_skills_interval', models.IntegerField(default=2, help_text="Specify how long (in seconds) between each activate skills execution, this is only used to control\nhow often skills are checked to see if they're ready to be activated.", verbose_name='Activate Skills Interval')),
                ('activate_skills_heavenly_strike_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('activate_skills_heavenly_strike_weight', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='0', max_length=255, verbose_name='Weight')),
                ('activate_skills_heavenly_strike_interval', models.IntegerField(default=0, verbose_name='Interval')),
                ('activate_skills_heavenly_strike_clicks', models.IntegerField(default=0, verbose_name='Clicks')),
                ('activate_skills_deadly_strike_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('activate_skills_deadly_strike_weight', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='0', max_length=255, verbose_name='Weight')),
                ('activate_skills_deadly_strike_interval', models.IntegerField(default=0, verbose_name='Interval')),
                ('activate_skills_deadly_strike_clicks', models.IntegerField(default=0, verbose_name='Clicks')),
                ('activate_skills_hand_of_midas_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('activate_skills_hand_of_midas_weight', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='0', max_length=255, verbose_name='Weight')),
                ('activate_skills_hand_of_midas_interval', models.IntegerField(default=0, verbose_name='Interval')),
                ('activate_skills_hand_of_midas_clicks', models.IntegerField(default=0, verbose_name='Clicks')),
                ('activate_skills_fire_sword_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('activate_skills_fire_sword_weight', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='0', max_length=255, verbose_name='Weight')),
                ('activate_skills_fire_sword_interval', models.IntegerField(default=0, verbose_name='Interval')),
                ('activate_skills_fire_sword_clicks', models.IntegerField(default=0, verbose_name='Clicks')),
                ('activate_skills_war_cry_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('activate_skills_war_cry_weight', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='0', max_length=255, verbose_name='Weight')),
                ('activate_skills_war_cry_interval', models.IntegerField(default=0, verbose_name='Interval')),
                ('activate_skills_war_cry_clicks', models.IntegerField(default=0, verbose_name='Clicks')),
                ('activate_skills_shadow_clone_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('activate_skills_shadow_clone_weight', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], default='0', max_length=255, verbose_name='Weight')),
                ('activate_skills_shadow_clone_interval', models.IntegerField(default=0, verbose_name='Interval')),
                ('activate_skills_shadow_clone_clicks', models.IntegerField(default=0, verbose_name='Clicks')),
                ('level_heroes_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling heroes in game.', verbose_name='Level Heroes Enabled')),
                ('level_heroes_skip_if_autobuy_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls skipping manual hero levelling when the\nautobuy feature is currently enabled in game.', verbose_name='Level Heroes Skip If Autobuy Enabled')),
                ('level_heroes_on_start', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling heroes once on session startup.', verbose_name='Level Heroes On Start')),
                ('level_heroes_interval', models.IntegerField(default=30, help_text='Specify how long (in seconds) between each level heroes execution.', verbose_name='Level Heroes Interval')),
                ('level_heroes_quick_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling heroes quickly in game.\nQuick hero levelling works similarly to the normal hero levelling function, except\nno drags are performed to travel to the first max level hero in game, or the bottom\nof the heroes panel.', verbose_name='Level Heroes Quick Enabled')),
                ('level_heroes_quick_on_start', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls levelling heroes quickly in game\nonce on session startup.', verbose_name='Level Heroes Quick Enabled')),
                ('level_heroes_quick_interval', models.IntegerField(default=20, help_text='Specify how long (in seconds) between each level heroes quick execution.', verbose_name='Level Heroes Quick Interval')),
                ('level_heroes_quick_loops', models.IntegerField(default=1, help_text='Specify how many times the quick hero levelling functionality is performed per execution,\none loop will level each hero on the screen once, increasing the number of loops may improve\nyour hero levelling efficiency.', verbose_name='Level Heroes Quick Loops')),
                ('level_heroes_masteries_unlocked', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls whether or not to level each hero once\nwhen levelling heroes in game. This will speed up the levelling process substantially\nif all of your heroes have at least one mastery.', verbose_name='Level Heroes Masteries Unlocked')),
                ('shop_pets_purchase_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls purchasing pets from the shop in game.', verbose_name='Shop Pet Purchase Enabled')),
                ('shop_pets_purchase_on_start', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls purchasing pets from the shop in game once\non session startup.', verbose_name='Shop Pet Purchase On Start')),
                ('shop_pets_purchase_interval', models.IntegerField(default=10800, help_text='Specify how long (in seconds) between each pets purchase execution.', verbose_name='Shop Pet Purchase Interval')),
                ('shop_pets_purchase_pets', models.TextField(default='', help_text='Specify a comma-separated list of in game pets to search for when attempting to purchase\npets from the in game shop. Example: "fluffers,kit,percy".', verbose_name='Shop Pet Purchase Pets')),
                ('shop_video_chest_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls the collection of the video chest from the\nshop in game.', verbose_name='Shop Video Chest Enabled')),
                ('shop_video_chest_on_start', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls the collection of the video chest from the\nshop in game once on session startup.', verbose_name='Shop Video Chest On Start')),
                ('shop_video_chest_interval', models.IntegerField(default=10800, help_text='Specify how long (in seconds) between each video chest execution.', verbose_name='Shop Video Chest Interval')),
                ('perks_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls buying and using perks in game.', verbose_name='Perks Enabled')),
                ('perks_on_start', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls buying and using perks in game\nonce on session startup.', verbose_name='Perks On Start')),
                ('perks_interval', models.IntegerField(default=3600, help_text='Specify how long (in seconds) between each perks execution.', verbose_name='Perks Interval')),
                ('perks_spend_diamonds', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls buying perks in game with diamonds,\nthis requires your account to have enough diamonds available to buy perks.', verbose_name='Perks Spend Diamonds')),
                ('perks_mega_boost_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('perks_mega_boost_tier', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')], default='1', max_length=255, verbose_name='Tier')),
                ('perks_power_of_swiping_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('perks_power_of_swiping_tier', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')], default='1', max_length=255, verbose_name='Tier')),
                ('perks_adrenaline_rush_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('perks_adrenaline_rush_tier', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')], default='1', max_length=255, verbose_name='Tier')),
                ('perks_make_it_rain_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('perks_make_it_rain_tier', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')], default='1', max_length=255, verbose_name='Tier')),
                ('perks_mana_potion_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('perks_mana_potion_tier', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')], default='1', max_length=255, verbose_name='Tier')),
                ('perks_doom_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('perks_doom_tier', models.CharField(choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3')], default='1', max_length=255, verbose_name='Tier')),
                ('perks_clan_crate_enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('headgear_swap_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls headgear swapping in game based on the most\npowerful hero currently in game. This functionality requires you to have locked pieces of headgear\nthat contain the proper damage type boost: ("warrior", "ranger", "mage"). If enabled, this function\nruns every time the hero levelling process is finished. Headgear is only swapped when the most\npowerful hero has changed from the last check in game.', verbose_name='Headgear Swap Enabled')),
                ('headgear_swap_check_hero_index', models.IntegerField(default=3, help_text='Specify which hero to look at when parsing the most powerful hero from the game, the default here is usually\nfine, but depending on how far along in the game you are, sometimes different hero indexes offer a bigger damage\nboost in game.', verbose_name='Headgear Swap Check Hero Index')),
                ('tournaments_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls tournament participation and rewards collection in game.\nNote: All tournament functionality is handled when a prestige takes place in game.', verbose_name='Tournaments Enabled')),
                ('prestige_time_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls automatic prestige based on a time interval.', verbose_name='Prestige Time Enabled')),
                ('prestige_time_interval', models.IntegerField(default=2700, help_text='Specify how long (in secondS) between each timed prestige execution in game.', verbose_name='Prestige Time Interval')),
                ('prestige_close_to_max_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls automatic prestige based on when you\'re "close" to\nyour max stage in game. This is handled in two ways, if an event is running in game, the "Prestige" icon on the master panel is checked for the current event icon, otherwise the skill tree is opened and the\n"Prestige To Reset" is searched for.', verbose_name='Prestige Close To Max Enabled')),
                ('prestige_close_to_max_fight_boss_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls automatic prestige based on when you\'re "close" to\nyour max stage (see "Prestige Close To Max Enabled" above) and the fight boss icon appears for the first\ntime after the close to max threshold is reached. This setting may or may not be more efficient for you\ndepending on your maximum stage and current end game status. Note: The "Prestige Wait When Ready Interval"\nis ignored when this is enabled, instead, as soon as the fight boss icon appears, a prestige is performed.', verbose_name='Prestige Close To Max Fight Boss Enabled')),
                ('prestige_wait_when_ready_interval', models.IntegerField(default=0, help_text='Specify how long (in secondS) to wait once a prestige is ready (based on the above toggles) before the\nprestige is actually performed.', verbose_name='Prestige Wait When Ready Interval')),
                ('artifacts_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls artifact enchantment/discovery/upgrades after a\nprestige is performed.', verbose_name='Artifacts Enabled')),
                ('artifacts_enchantment_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls artifact enchantment in game.', verbose_name='Artifacts Enchantment Enabled')),
                ('artifacts_discovery_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls artifact discovery in game.', verbose_name='Artifacts Discovery Enabled')),
                ('artifacts_discovery_upgrade_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls upgrading artifacts after discovering\none in game.', verbose_name='Artifacts Discovery Upgrade Enabled')),
                ('artifacts_discovery_upgrade_multiplier', models.CharField(default='max', help_text='Specify the in game upgrade multiplier used when upgrading a newly discovered artifact\nin game. Choose one of: "max", "25", "5", "1".', max_length=255, verbose_name='Artifact Discovery Upgrade Multiplier')),
                ('artifacts_upgrade_enabled', models.BooleanField(default=True, help_text='Enable/disable the functionality that controls upgrading selected artifacts after a prestige\nis performed in game.', verbose_name='Artifacts Upgrade Enabled')),
                ('artifacts_upgrade_artifacts', models.TextField(default='book_of_shadows', help_text='Specify a comma-separated list of in game artifacts to upgrade after a prestige is performed\nin game. Example: "book_of_shadows,stone_of_the_valrunes,heroic_shield".', verbose_name='Artifacts Upgrade Artifacts')),
                ('artifacts_shuffle_enabled', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls shuffling of artifacts specified in the comma-separated\nlist above. This will also shuffle the list of artifacts to upgrade on every subsequent prestige.', verbose_name='Artifacts Shuffle Enabled')),
            ],
        ),
        migrations.CreateModel(
            name='Instance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default=database.models.instance.get_default_instance_name, help_text='Specify a name for this instance, the instance name is only used for informational purposes and has no bearing on any bot functionality.', max_length=255, verbose_name='Name')),
            ],
        ),
        migrations.CreateModel(
            name='Settings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('failsafe', models.BooleanField(default=True, help_text='Enable/disable the "failsafe" functionality while a bot is actively running. A failsafe exception will be\nencountered if this is enabled and your mouse cursor is in the TOP LEFT corner of your primary monitor. Note that\nrunning other windows or tasks in fullscreen mode may also raise failsafe exceptions if you\'re using the bot in\nthe background. Defaults to "True".', verbose_name='Failsafe')),
                ('ad_blocking', models.BooleanField(default=False, help_text='Enable/disable the functionality that controls whether or not the "watch" button is clicked on when encountered\nin game. This function will only work if you have an external ad blocker actively running while playing the game.\nDefaults to "False".', verbose_name='Ad Blocking')),
                ('log_level', models.CharField(choices=[('DEBUG', 'DEBUG'), ('ERROR', 'ERROR'), ('WARNING', 'WARNING'), ('INFO', 'INFO')], default='INFO', help_text='Determine the log level used when displaying logs while a bot session is running. This setting is only applied\non session startup, if this is changed while a session is running, you\'ll need to restart your session for the\nlog level to be changed.\nDefaults to "INFO".', max_length=255, verbose_name='Log Level')),
                ('log_purge_days', models.IntegerField(default=3, help_text='Specify the number of (days) to retain any logs, "stale" logs are purged once their modification date has surpassed\nthe number of days specified here. Defaults to "3".', verbose_name='Log Purge (Days)')),
                ('console_size', models.CharField(default='mode con: cols=140 lines=200', max_length=255)),
                ('last_window', models.CharField(default=None, max_length=255, null=True)),
                ('last_configuration', models.CharField(default=None, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=datetime.datetime.now, help_text='The timestamp associated with this event.', verbose_name='Timestamp')),
                ('event', models.CharField(help_text='The event description.', max_length=255, verbose_name='Event')),
                ('instance', models.ForeignKey(help_text='The instance associated with an event.', on_delete=django.db.models.deletion.CASCADE, related_name='events', to='database.instance', verbose_name='Instance')),
            ],
        ),
    ]
