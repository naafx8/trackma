#!/usr/bin/python

# wMAL v0.1
# Lightweight terminal-based script for using data from MyAnimeList.
# Copyright (C) 2012  z411
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import readline
import cmd
import re
from operator import itemgetter # Used for sorting list

import messenger
import engine
import utils

_DEBUG = True
_COLOR_ENGINE = '\033[0;32m'
_COLOR_DATA = '\033[0;33m'
_COLOR_API = '\033[0;34m'
_COLOR_ERROR = '\033[0;31m'
_COLOR_FATAL = '\033[1;31m'
_COLOR_RESET = '\033[0m'

_COLOR_AIRING = '\033[0;34m'

class wmal_cmd(cmd.Cmd):
    """
    Main program, inherits from the useful Cmd class
    for interactive console
    """
    engine = None
    filter_num = 1
    sort = 'title'
    
    __re_cmd = re.compile(r"([-\w]+|\".*\")")   # Args parser
    
    def start(self):
        """
        Initializes the engine
        
        Creates an Engine object and starts it.
        """
        print 'wMAL v0.1  Copyright (C) 2012  z411'
        print 'This program comes with ABSOLUTELY NO WARRANTY; for details type `license\''
        print 'This is free software, and you are welcome to redistribute it'
        print 'under certain conditions; type `license conditions\' for details.'
        print
        print 'Initializing engine...'
        self.engine = engine.Engine(self.messagehandler)
        return self.engine.start()
    
    def do_filter(self, arg):
        """
        filter - Changes the filtering of list by status
        
        Usage: filter <filter type>
        """
        # Query the engine for the available statuses
        # that the user can choose
        statuses = self.engine.statuses()
        statuses_keys = self.engine.statuses_keys()
        if arg:
            try:
                self.filter_num = statuses_keys[arg]
                self.prompt = 'wMAL ' + statuses[self.filter_num] + '> '
            except KeyError:
                print "Invalid filter."
        else:
            print "Missing arguments."
    
    def do_sort(self, arg):
        """
        sort - Change sort
        
        Usage: sort <sort type>
        Available types: id, title, my_episodes, episodes
        """
        sorts = ('id', 'title', 'my_episodes', 'episodes')
        if arg in sorts:
            self.sort = arg
        else:
            print "Invalid sort."
        
    def do_list(self, arg):
        """
        list - Lists all shows available as a nice formatted list.
        """
        # Queries the engine for a list and sorts it
        # using the current sort
        showlist = self.engine.filter_list(self.filter_num)
        sortedlist = sorted(showlist, key=itemgetter(self.sort)) 
        make_list(sortedlist)
    
    def do_search(self, arg):
        """
        search - Does a regex search on shows and lists the matches.
        
        Usage: search <pattern>
        """
        if(arg):
            showlist = self.engine.regex_list(arg)
            sortedlist = sorted(showlist, key=itemgetter(self.sort)) 
            make_list(sortedlist)
        else:
            print "Missing arguments."
    
    def do_play(self, arg):
        if arg:
            try:
                args = self.parse_args(arg)
                show = self.engine.get_show_info(args[0])
                episode = 0
                
                # If the user specified an episode, play it
                # otherwise play the next episode not watched yet
                try:
                    episode = args[1]
                    if episode == (show['my_episodes'] + 1):
                        playing_next = True
                    else:
                        playing_next = False
                except IndexError:
                    playing_next = True
                
                played_episode = self.engine.play_episode(show, episode)
                
                # Ask if we should update the show to the last episode
                if played_episode and playing_next:
                    do_update = raw_input("Should I update %s to episode %d? [y/N]" % (show['title'], played_episode))
                    if do_update.lower() == 'y':
                        self.engine.set_episode(show['id'], played_episode)
            except utils.wmalError, e:
                self.display_error(e)
        else:
            print "Missing arguments."
        
    def do_update(self, arg):
        """
        update - Updates the episode of a show.
        
        Usage: update <show id or name> <episode number>
        """
        if arg:
            args = self.parse_args(arg)
            try:
                self.engine.set_episode(args[0], args[1])
            except IndexError:
                print "Missing arguments."
            except utils.wmalError, e:
                self.display_error(e)
        else:
            print "Missing arguments."
        
    def do_quit(self, arg):
        """Quits the program."""
        self.engine.unload()
        print 'Bye!'
        sys.exit(0)
        
    def complete_update(self, text, line, begidx, endidx):
        if text:
            return self.engine.regex_list_titles(text)
    
    def complete_play(self, text, line, begidx, endidx):
        if text:
            return self.engine.regex_list_titles(text)
    
    def parse_args(self, arg):
        if arg:
            return list(v.strip('"') for v in self.__re_cmd.findall(arg))
    
    def display_error(self, e):
        print "%s%s: %s%s" % (_COLOR_ERROR, type(e), e.message, _COLOR_RESET)
    
    def messagehandler(self, classname, msgtype, msg):
        """
        Handles and shows messages coming from
        the engine messenger to provide feedback.
        """
        color_escape = ''
        color_reset = _COLOR_RESET
        
        if classname == 'Engine':
            color_escape = _COLOR_ENGINE
        elif classname == 'Data':
            color_escape = _COLOR_DATA
        elif classname.startswith('lib'):
            color_escape = _COLOR_API
        else:
            color_reset = ''
        
        if msgtype == messenger.TYPE_INFO:
            print "%s%s: %s%s" % (color_escape, classname, msg, color_reset)
        elif msgtype == messenger.TYPE_WARN:
            print "%s%s warning: %s%s" % (color_escape, classname, msg, color_reset)
        elif _DEBUG and msgtype == messenger.TYPE_DEBUG:
            print "%s%s: %s%s" % (color_escape, classname, msg, color_reset)

def make_list(showlist):
    """
    Helper function for printing a formatted show list
    """
    # Fixed column widths
    col_id_length = 7
    col_title_length = 5
    col_episodes_length = 9
    
    # Calculate maximum width for the title column
    # based on the width of the terminal
    (height, width) = utils.get_terminal_size()
    max_title_length = width - col_id_length - col_episodes_length - 5
    
    # Find the widest title so we can adjust the title column
    for show in showlist:
        if len(show['title']) > col_title_length:
            if len(show['title']) > max_title_length:
                # Stop if we exceeded the maximum column width
                col_title_length = max_title_length
                break
            else:
                col_title_length = len(show['title'])
        
    # Print header
    print "| {0:{1}} {2:{3}} {4:{5}}|".format(
            'ID',       col_id_length,
            'Title',    col_title_length,
            'Episodes', col_episodes_length)
    
    # List shows
    for show in showlist:
        episodes_str = "{0:3} / {1}".format(show['my_episodes'], show['episodes'])
        
        # Truncate title if needed
        title_str = show['title']
        title_str = title_str[:max_title_length] if len(title_str) > max_title_length else title_str
        
        # Color title according to status
        if show['status'] == 1:
            colored_title = _COLOR_AIRING + title_str + _COLOR_RESET
        else:
            colored_title = title_str
        
        print "| {0:<{1}} {2}{3} {4:{5}}|".format(
            show['id'],     col_id_length,
            colored_title,  '.' * (col_title_length-len(show['title'].decode('utf-8'))),
            episodes_str,   col_episodes_length)
    
    # Print result count
    print '%d results' % len(showlist)
    print
    
if __name__ == '__main__':
    main_cmd = wmal_cmd()
    main_cmd.prompt = 'wMAL Watching> '
    try:
        main_cmd.start()
        print
        print "Ready. Type 'help' for a list of commands."
        print "Press tab for autocompletion and up/down for command history."
        print
        main_cmd.cmdloop()
    except utils.wmalFatal, e:
        print "%s%s: %s%s" % (_COLOR_FATAL, type(e), e.message, _COLOR_RESET)
    
