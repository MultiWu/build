# -*- coding: utf-8 -*-

import urlparse
from oathscrapers import sources_oathscrapers
from oathscrapers.modules import control
from oathscrapers import providerSources, providerNames


params = dict(urlparse.parse_qsl(sys.argv[2].replace('?', '')))
action = params.get('action')
mode = params.get('mode')
query = params.get('query')



def ScraperChoice():
    from oathscrapers import providerSources
    sourceList = sorted(providerSources())
    control.idle()
    select = control.selectDialog([i for i in sourceList])
    if select == -1: return
    module_choice = sourceList[select]
    control.setSetting('package.folder', module_choice)
    control.openSettings('0.1')

def ToggleProviderAll(enable):
    from oathscrapers import providerNames
    sourceList = providerNames()
    (setting, open_id) = ('true', '0.3') if enable else ('false', '0.2')
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, setting)
    control.openSettings(open_id)


if action == "oathscrapersettings":
    control.openSettings('0.0', 'script.module.oathscrapers')

elif mode == "oathscrapersettings":
    control.openSettings('0.0', 'script.module.oathscrapers')


elif action == "ScraperChoice":
    ScraperChoice()


elif action == "toggleAll":
    sourcelist = []
    sourceList = sources_oathscrapers.all_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "ToggleProviderAll":
    ToggleProviderAll(False if params['action'] == "DisableModuleAll" else True)


elif action == "toggleAllHosters":
    sourcelist = []
    sourceList = sources_oathscrapers.hoster_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Hoster providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllForeign":
    sourcelist = []
    sourceList = sources_oathscrapers.all_foreign_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Foregin providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllSpanish":
    sourcelist = []
    sourceList = sources_oathscrapers.spanish_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Spanish providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllGerman":
    sourcelist = []
    sourceList = sources_oathscrapers.german_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All German providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllGreek":
    sourcelist = []
    sourceList = sources_oathscrapers.greek_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Greek providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllPolish":
    sourcelist = []
    sourceList = sources_oathscrapers.polish_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Polish providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllPaid":
    sourcelist = []
    sourceList = sources_oathscrapers.all_paid_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Paid providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllDebrid":
    sourcelist = []
    sourceList = sources_oathscrapers.debrid_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Debrid providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


elif action == "toggleAllTorrent":
    sourceList = []
    sourceList = sources_oathscrapers.torrent_providers
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
#    xbmc.log('All Torrent providers = %s' % sourceList,2)
    control.openSettings(query, "script.module.oathscrapers")


if action == "Defaults":
    sourceList = ['123fox','123hbo','123movieshubz','animetoon','azmovies','bnwmovies','cartoonhd',
    'extramovies','fmovies','freefmovies','freeputlockers','gostream','Hdmto','hdpopcorns',
    'kattv','l23movies','iwaatch','openloadmovie','primewire','putlocker','reddit','rlsbb','scenerls',
    'seehd','series9','seriesfree','seriesonline','solarmoviez','tvbox','vidics','watchseries',
    'xwatchseries','vdonip','downflix','ymovies','ddlspot','filmxy','kickass2','sezonlukdizi']
    for i in sourceList:
        source_setting = 'provider.' + i
        control.setSetting(source_setting, params['setting'])
    control.openSettings(query, "script.module.oathscrapers")

