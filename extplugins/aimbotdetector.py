#
# Aimbot Detector Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011 Freelander - www.fps-gamer.net
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
# 22.03.2011 - 1.1 - Freelander
#   * Added keyword "aimbotdetector" to display in echelon
#   * Ability to check more than one hit location
#   * Can choose between options; kick, tempban, permban or notify only
#   * Minor enhancements
# 25.06.2011 - 1.2 - Freelander
#   * Option to send e-mail to selected e-mail address(es) when a suspicious
#     player is detected
#

## @file
#  This plugin checks for possible cheaters using aimbot.

__author__  = 'Freelander'
__version__ = '1.2'

import b3
import b3.events
import b3.plugin
import time
import smtplib

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

        self._actions = ['kick', 'tempban', 'permban', 'notify only']

        self.debug('Aimbot Detector Plugin is set to %s' % self._actions[self.action])

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

        # Get e-mail settings
        try:
            self.mailtoadmin = self.config.getboolean('mail', 'mailtoadmin')
        except:
            self.mailtoadmin = False
            self.debug('Cannot load e-mail option, disabling...')

        if self.mailtoadmin:
            self.info('E-mail feature is enabled!')
        else:
            self.info('E-mail feature is disabled!')

        if self.mailtoadmin:
            try:
                self.servername = self.config.get('mail', 'servername')
                self.sendername = self.config.get('mail', 'sendername')
                self.sendermail = self.config.get('mail', 'sendermail')
                self.receivers = self.config.get('mail', 'receivers')
                self.smtp = self.config.get('mail', 'smtp')
                self.login = self.config.get('mail', 'login')
                self.password = self.config.get('mail', 'password')
                self.emailbody = self.config.get('mail', 'emailbody')
            except:
                self.debug('Cannot load e-mail settings, please check your config file. Disabling e-mailing feature...')
                self.mailtoadmin = False

        self.debug('Starting')

    def onStartup(self):
        # get the plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        self._followPlugin = self.console.getPlugin('follow')
        if self._followPlugin:
            self.info('Found the follow plugin, hooking in to it.')

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
                    self.addFollow(client)
                elif self.action == 1:
                    self.debug('Temporarily Banning Player')
                    client.tempban(reason=self.kickmessage, keyword="aimbotdetector", duration=self.duration, data="%s kills" % hitloc_kills)
                    self.addFollow(client)
                elif self.action == 2:
                    self.debug('Permanently Banning Player')
                    client.ban(reason=self.kickmessage, keyword="aimbotdetector", data="%s kills" % hitloc_kills)
                elif self.action == 3:
                    self.debug('Sending PM to all admins online')
                    self.pmAdmins(client.name)
                    self.addFollow(client)

            if hitloc_kills == self.treshold: #send alert mail only once
                if self.mailtoadmin:
                    self.mail2Admins(client)

    def pmAdmins(self, suspect):
        """Send a PM message to connected admins"""

        clients = self.console.clients.getList()
        for player in clients:
            if player.maxLevel >= self.adminlevel:
                player.message(self.warnmessage % suspect)
                time.sleep(1)

    def addFollow(self, sclient):
        """Add the suspect to the follow plugin database if installed"""

        if not self._followPlugin:
            return None

        # if we have a hook to the follow plugin, let's tag the suspect to be followed
        cursor = self.console.storage.query(self._followPlugin._SELECT_QUERY % sclient.id)
        if cursor.rowcount == 0:
            cursor2 = self.console.storage.query(
                self._followPlugin._ADD_QUERY % (sclient.id, 0, self.console.time(), 'Tagged by Aimbotdetector!'))
            cursor2.close()
            self.debug("Suspect added to follow plugins watch list")
        else:
            self.debug("Suspect already in follow plugins watch list")
        cursor.close()
        self._followPlugin.sync_list(None)

    def mail2Admins(self, client=None):
        """Send mail to admin(s)"""

        if ',' in self.receivers:
            receivers = self.receivers.split(',')
            m = []
            for r in receivers:
                m.append('<%s>' % r.strip())
            receivers_address = ', '.join(m)
        else:
            receivers_address = '<%s>' % self.receivers
            receivers = self.receivers

        self.debug('Sending alert e-mail to %s' % receivers)

        message  = 'From: %s <%s>\n' % (self.sendername, self.sendermail)
        message += 'To: %s\n' % receivers_address
        message += 'Date: %s\n' % time.ctime(time.time())
        message += 'Subject: [B3]Aimbot Detector Alert!!!\n'
        message += '%s\n\n' % self.emailbody
        message += '=========================================================\n'
        message += 'INFORMATION\n'
        message += '---------------------------------------------------------\n'
        message += 'Date/Time    : %s\n' % time.ctime(time.time())
        message += 'Server Name  : %s\n' % self.servername
        message += 'Player Name  : %s\n' % client.name
        message += 'IP           : %s\n' % client.ip
        message += 'GUID         : %s\n' % client.guid
        message += 'Action Taken : %s\n' % self._actions[self.action].title()
        message += '---------------------------------------------------------\n'

        try:
            smtpObj = smtplib.SMTP(self.smtp)
            smtpObj.starttls()
            smtpObj.login(self.login, self.password)
            smtpObj.sendmail(self.sendermail, receivers, message)         
            self.info('Successfully sent e-mail')
        except Exception, err:
            self.debug('Error: unable to send e-mail: %s' % err)

#-------------------------------------------------------------------------------------

if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe, simon, moderator, superadmin

    from b3.config import XmlConfigParser

    conf = XmlConfigParser()
    conf.setXml('''\
    <configuration plugin="aimbotdetector">
        <!-- Hit location console code. You can add more than one location although not recommended! -->
        <hitlocs>
            <hitloc>head</hitloc>
        </hitlocs>
        <settings name="settings">
            <!-- 
            Number of killstreak for the specific hitlocation. When the number 
            specified here is reached, either the client will be kicked or online admins
            get notified depending on your selection
            -->
            <set name="treshold">2</set>
            <!-- 
            You can choose different actions when the player reaches the treshold.
            Please write the corresponding number of the action of your choice:
            Kick        : 0
            Tempban     : 1
            Permban     : 2
            Notify Only : 3
            -->
            <set name="action">0</set>
            <!--
            If you have chosen to tempban the player, you can define a duration
            as in B3 duration format.
            Example:
            6m : 6 Minutes
            2h : 2 Hours
            1w : 1 Week
            3d : 3 Days
            -->
            <set name="duration">2h</set>
            <!--
            If you have chosen to notify online admins, all admins equal or higher level will get 
            notified via PM
            -->
            <set name="adminlevel">40</set>
            <!-- Minimum level to ignore. i.e. players with equal or higher level will not be checked -->
            <set name="ignorelevel">40</set>
        </settings>
        <settings name="messages">
            <set name="warnmessage">^1ATTENTION: ^7%s maybe using aimbot! Better check it out.</set>
            <set name="kickmessage">^1Aimbot Detected!</set>
        </settings>
        <settings name="mail">
            <!-- Do you want to send e-mail to admin(s) when the bot detects a suspicious player? -->
            <set name="mailtoadmin">yes</set>
            <!-- Your game server name to be included in e-mail message. Useful if you have multiple servers -->
            <set name="servername">Game Server Name</set>
            <!-- Sender's Real Name -->
            <set name="sendername">Your Name</set>
            <!-- Sender's e-mail address -->
            <set name="sendermail">you@example.com</set>
            <!-- Receivers' e-mail addresses (separate with comma (,)) -->
            <set name="receivers">admin_1@example.com, admin_2@example.com</set>
            <!-- Your SMTP server Example: mail.example.com. For Google that is smtp.gmail.com:587 -->
            <set name="smtp">mail.example.com</set>
            <!-- E-mail login name -->
            <set name="login">login_name</set>
            <!-- E-mail password -->
            <set name="password">password</set>
            <!-- Your E-mail message body -->
            <set name="emailbody">Attention! A suspicious player detected, better get your ass into the server</set>
        </settings>
    </configuration>
    ''')

    p = AimbotdetectorPlugin(fakeConsole, conf)
    p.onStartup()

    print '------------------------------'
    joe.connects(cid=1)
    joe.ip = '111.222.333.444'
    superadmin.connects(cid=3)
    moderator.connects(cid=5)
    simon.connects(cid=7)
    joe.kills(superadmin)
    print '------------------------------'
    joe.kills(superadmin)
    print '------------------------------'
    joe.kills(superadmin)