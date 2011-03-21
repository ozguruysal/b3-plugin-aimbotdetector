# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2010
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
#  The core funstionality of this plugin is inspired from spree plugin by Walker.
#
# CHANGELOG
#
# 17.03.2011 - 1.0 - Freelander
#   * Initial release
#  testing
## @file
#  This plugin checks for possible cheaters using aimbot.

__author__  = 'Freelander'
__version__ = '1.0'

import b3
import b3.events

class HitlocStats:
    """Check for players killstreak for a set hit location
    that is generally headshots"""

    hitloc_kills = 0

#-------------------------------------------------------------------------------------

class AimbotdetectorPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _clientvar_name = 'hitloc_killstreak'

    def onLoadConfig(self):
        """Load setting from plugin config file"""

        # Get the settings from the config.
        self.hitloc = self.config.get('settings', 'hitloc')
        self.treshold = self.config.getint('settings', 'treshold')
        self.debug('Players with %s %s kills in a row will be detected by Aimbot Detector' % (self.treshold, self.hitloc))
        self.adminlevel = self.config.getint('settings', 'adminlevel')
        self.ignorelevel = self.config.getint('settings', 'ignorelevel')
        self.debug('Players with level %s and above will not be checked' % self.ignorelevel)
        self.kick = self.config.getint('settings', 'kick')

        if self.kick == 1:
            self.debug('Aimbot Detector Plugin is set to kick')
        else:
            self.debug('Aimbot Detector Plugin is set to notify admins online')

        # Get the messages from the config.
        self.warnmessage = self.config.get('messages', 'warnmessage')
        self.kickmessage = self.config.get('messages', 'kickmessage')

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
            if damage_location == self.hitloc:
                HitlocStats.hitloc_kills += 1
                self.debug('%s has a %s %s kill streak' % (client.name, HitlocStats.hitloc_kills, self.hitloc))
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
                if self.kick == 1:
                    self.debug('Kicking Player')
                    client.kick(self.kickmessage)
                else:
                    self.debug('Sending PM to all admins online')
                    self.pmAdmins(client.name)

    def pmAdmins(self, suspect):
        """Send a PM message to connected admins"""

        clients = self.console.clients.getList()
        for player in clients:
            if player.maxLevel >= self.adminlevel:
                player.message(self.warnmessage % suspect)
                time.sleep(0.5)
