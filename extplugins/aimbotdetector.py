# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#  NOTES:
#  The idea of this plugin was suggested by B3 forum user Dragon25
#  The core functionality of this plugin is inspired from spree plugin by Walker.
#
# CHANGELOG
#
# 17.03.2011 - 1.0 - Freelander
#   * Initial release
# 21.03.2011 - 1.1 - Freelander
#   * Added keyword "aimbotdetector" to display in echelon where available
#   * Ability to check more than one hit location
#   * Can choose between options; kick, tempban, permban or notify only
#   * Minor code enhancements
#

## @file
#  This plugin checks for possible cheaters using aimbot.

__author__  = 'Freelander'
__version__ = '1.1'

import b3
import b3.events
import b3.plugin
import time

class HitlocStats:
    """Check for players killstreak for a set hit location
    that is generally headshots"""

    hitloc_kills = 0

class Hitlocations:
    _hitloc = None

#-------------------------------------------------------------------------------------

class AimbotdetectorPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _clientvar_name = 'hitloc_killstreak'
    _hitlocs = []

    def onLoadConfig(self):
        """Load settings from plugin config file"""

        # Get the settings from the config.
        try:
            for i in self.config.get('hitlocs/hitloc'):
                _hl = Hitlocations()
                _hl._hitloc = i.text.strip()
                self._hitlocs.append(_hl._hitloc)
                self.debug('Checking hitlocation :: %s' % _hl._hitloc)
        except:
            self._hitlocs = ['head']
            self.debug('Using default hitlocation :: head')
        try:
            self.treshold = self.config.getint('settings', 'treshold')
        except:
            self.treshold = 15
            self.debug = ('Using default treshold value (%s)' % self.treshold)
        #self.debug('Players with %s %s kills in a row will be detected by Aimbot Detector' % (self.treshold, self.hitloc))
        try:
            self.adminlevel = self.config.getint('settings', 'adminlevel')
        except:
            self.adminlevel = 40
            self.debug = ('Using default adminlevel value (%s)' % self.adminlevel)
        try:
            self.ignorelevel = self.config.getint('settings', 'ignorelevel')
        except:
            self.ignorelevel = 40
            self.debug = ('Using default ignorelevel value (%s)' % self.ignorelevel)
        self.debug('Players with level %s and above will not be checked' % self.ignorelevel)
        try:
            self.action = self.config.getint('settings', 'action')
        except:
            self.action = 1

        _actions = ['kick', 'tempban', 'permban', 'notify only']
        for i in _actions:
            _choice = _actions[self.action]

        self.debug('Aimbot Detector Plugin is set to %s' % _actions[self.action])

        if self.action == 1:
            try:
                self.duration = self.config.get('settings', 'duration')
                self.debug('Tempban duration is: %s' % self.duration)
            except:
                self.duration = '2h'
                self.debug('Using default tempban duration %s' % self.duration)

        # Get the messages from the config.
        try:
            self.warnmessage = self.config.get('messages', 'warnmessage')
        except:
            self.warnmessage = '^1ATTENTION: ^7%s maybe using aimbot! Better check it out.'
        try:
            self.kickmessage = self.config.get('messages', 'kickmessage')
        except:
            self.kickmessage = '^1Aimbot Detected!'

        self.debug('Starting')

    def onStartup(self):
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        # listen for client events
        self.verbose('Registering events')
        self.registerEvent(b3.events.EVT_CLIENT_KILL)

        self.debug('Started')

    def handle(self, event):
        """Handle intercepted events"""

        if event.type == b3.events.EVT_CLIENT_KILL:
            damage_location = event.data[2]
            self.checkHitlocKills(event.client, event.target, damage_location)

    def getHitlocStats(self, client):
        """Get the clients killstreak for a specific hitlocation"""
        
        if not client.isvar(self, self._clientvar_name):
            # initialize the default HitlocStats object
            # we don't just use the client.var(...,default) here so we
            # don't create a new HitlocStats object for no reason every call
            client.setvar(self, self._clientvar_name, HitlocStats())
            
        return client.var(self, self._clientvar_name).value

    def checkHitlocKills(self, client=None, victim=None, damage_location=None):
        """Checks hitlocation of kill"""

        # client (attacker)
        if client:
            # we grab our HitlocStats object here
            # any changes to its values will be saved "automagically"
            HitlocStats = self.getHitlocStats(client)
            
            #check hitlocation of the kill is the hitlocation we are watching
            #if it is, add it to player's streak. Otherwise the player is shooting different
            #bodyparts each time so we reset his hitloc streak
            if damage_location in self._hitlocs:
                HitlocStats.hitloc_kills += 1
                self.debug('%s has a %s kill streak for monitored bodyparts' % (client.name, HitlocStats.hitloc_kills))
                self.checkHitlocKillStreak(HitlocStats.hitloc_kills, client)
            else:
                HitlocStats.hitloc_kills = 0
                #self.debug('Hitloc killstreak was reset for %s' % client.name)

    def checkHitlocKillStreak(self, hitloc_kills, client=None):
        """chekcs if the clients current hitloc killstreak reaches to theshold set
        and acts accordingly"""

        if client.maxLevel < self.ignorelevel:
            if hitloc_kills >= self.treshold: #Set it to greater or equal to just in case rcon send fails
                self.debug('%s has got %s hitloc kills in a row and reached treshold level' % (client.name, self.treshold))
                if self.action == 0:
                    self.debug('Kicking Player')
                    client.kick(reason=self.kickmessage, keyword="aimbotdetector", data="%s kills" % hitloc_kills)
                elif self.action == 1:
                    self.debug('Temporarily Banning Player')
                    client.tempban(reason=self.kickmessage, keyword="aimbotdetector", duration=self.duration, data="%s kills" % hitloc_kills)
                elif self.action == 2:
                    self.debug('Permanently Banning Player')
                    client.ban(reason=self.kickmessage, keyword="aimbotdetector", data="%s kills" % hitloc_kills)
                elif self.action == 3:
                    self.debug('Sending PM to all admins online')
                    self.pmAdmins(client.name)

    def pmAdmins(self, suspect):
        """Send a PM message to connected admins"""

        clients = self.console.clients.getList()
        for player in clients:
            if player.maxLevel >= self.adminlevel:
                player.message(self.warnmessage % suspect)
                time.sleep(0.5)


if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin
    import time

    from b3.config import XmlConfigParser

    conf = XmlConfigParser()
    conf.setXml("""\
    <configuration plugin="aimbotdetector">
        <hitlocs>
            <hitloc>1</hitloc>
        </hitlocs>
        <settings name="settings">
            <set name="treshold">3</set>
            <set name="action">1</set>
            <set name="duration">2h</set>
            <set name="adminlevel">40</set>
            <set name="ignorelevel">40</set>
        </settings>
        <settings name="messages">
            <set name="warnmessage">^1ATTENTION: ^7%s maybe using aimbot! Better check it out.</set>
            <set name="kickmessage">^1Aimbot Detected!</set>
        </settings>
    </configuration>

    """)
    traceback = ''
    p = AimbotdetectorPlugin(fakeConsole, conf)
    p.onStartup()

    print '------------------------------'
    joe.connects(cid=1)
    superadmin.connects(cid=3)
    joe.kills(superadmin)
    print '------------------------------'
    joe.kills(superadmin)
    print '------------------------------'
    joe.kills(superadmin)