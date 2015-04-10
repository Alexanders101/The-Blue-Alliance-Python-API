__author__ = 'alex'

from sys import version_info
if version_info[0] == 2: # Python 2.x
    import urllib2 as REQUEST
elif version_info[0] == 3: # Python 3.x
    from urllib import request as REQUEST

import json
import numpy as np

# For optimization
from numpy import zeros as np_zeros
from numpy import object as np_object
from numpy import array as np_array
from numpy import int as np_int
from numpy import rot90 as np_rot90
from numpy import arange as np_arange
from numpy import vstack as np_vstack
from numpy import concatenate as np_concatenate
from joblib import dump, load



class APIBase(object):
    URL = 'http://www.thebluealliance.com/api/v2/'
    HEADER = 'X-TBA-App-Id'
    VALUE = 'name:program:version'

    def __init__(self, name, program_name, program_version):
        self.VALUE = '%s:%s:%s' % (name, program_name, program_version)

    def _pull_request(self, request_code):
        request = REQUEST.Request(request_code)
        request.add_header(self.HEADER, self.VALUE)
        response = REQUEST.urlopen(request)
        response = json.loads(response.read().decode("utf-8"))
        return response

    def save_database(self, file_path):
        """Saves the current data to disk

        Keyword Arguments:
        file_path (str) -- Path were youo wish to save the file, use an extension like .db"""

        dump(self, file_path, True)


class Event(APIBase):

    EVENT_KEY = 'yyyyaaaa'

    def __init__(self, name, program_name, program_version, event_key):
        """Primary class for handling Event data

        name (str) -- name to identify you
        program_name (str) -- name or description of your program
        program_version (str) -- Version of your program
        event_key (str) -- key to identify your event,
            you can get keys for all of the events by running TheBlueAlliance.get_events_and_codes()"""
        super(Event, self).__init__(name, program_name, program_version)
        self.EVENT_KEY = event_key

        self.qualification_matches = []
        self.quarter_final_matches = []
        self.semi_final_matches = []
        self.final_matches = []

        self.raw_event = self._pull_request(self.URL + 'event/' + self.EVENT_KEY)
        self.raw_teams = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/teams')
        self.raw_matches = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/matches')
        self.raw_rankings = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/rankings')
        self.raw_stats = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/stats')
        self.raw_awards = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/awards')

        self.__init_matches()
        self.__init_statistics()
        self.__init_rankings()
        self.__init_teams()
        self.__init_event()
        self.__init_alliances()
        self.__init_awards()

    def __init_matches(self):

        for match_type, var in [['qm', 'qualification_matches'], ['qf', 'quarter_final_matches'],
                                ['sf', 'semi_final_matches'], ['f', 'final_matches']]:
            num_matches = self.__count_matches(self.raw_matches, match_type)
            if num_matches is not 0:
                # zero = range(num_matches)
                red_teams = np_zeros((num_matches,), np_object)
                blue_teams = np_zeros((num_matches,), np_object)
                blue_scores = np_zeros((num_matches,), np_object)
                red_scores = np_zeros((num_matches,), np_object)
                match_code = np_zeros((num_matches,), np_object)
                match_numbers = np_arange(1, num_matches + 1, 1)

                for match in self.raw_matches:
                    if match['comp_level'] == match_type:
                        match_num = match['match_number'] - 1

                        red_teams[match_num] = [np_int(match['alliances']['red']['teams'][0][3:]),
                                                np_int(match['alliances']['red']['teams'][1][3:]),
                                                np_int(match['alliances']['red']['teams'][2][3:])]

                        red_scores[match_num] = [-1 if match['alliances']['red']['score'] is None
                                                 else match['alliances']['red']['score'],
                                                 -1 if match['score_breakdown']['red']['auto'] is None
                                                 else match['score_breakdown']['red']['auto'],
                                                 -1 if match['score_breakdown']['red']['foul'] is None
                                                 else match['score_breakdown']['red']['foul']]

                        blue_teams[match_num] = [np_int(match['alliances']['blue']['teams'][0][3:]),
                                                 np_int(match['alliances']['blue']['teams'][1][3:]),
                                                 np_int(match['alliances']['blue']['teams'][2][3:])]

                        blue_scores[match_num] = [-1 if match['alliances']['blue']['score'] is None
                                                  else match['alliances']['blue']['score'],
                                                  -1 if match['score_breakdown']['blue']['auto'] is None
                                                  else match['score_breakdown']['blue']['auto'],
                                                  -1 if match['score_breakdown']['blue']['foul'] is None
                                                  else match['score_breakdown']['blue']['foul']]
                        match_code[match_num] = match['key']

                red_win = np_array(red_scores.tolist())[:, 0] > np_array(blue_scores.tolist())[:, 0]
                winner = np_array(['blue'] * len(red_win))
                winner[red_win] = 'red'

                self.__setattr__(var,
                                 np_rot90(np_array([[match_type] * num_matches, match_numbers, red_teams, blue_teams,
                                                    red_scores, blue_scores, winner, match_code], np_object))[::-1])

    def __init_rankings(self):
        self.rankings = np_array(self.raw_rankings[1:]).astype(np_int)

    def __init_statistics(self):
        stats = self.raw_stats
        if stats is not None:
            combined = np_array([[int(team), stats['oprs'][team], stats['dprs'][team],
                                  stats['ccwms'][team]] for team in stats['oprs'].keys()], np_object)
        else:
            teams = self.get_team()[:, 0]
            num_teams = len(teams)
            combined = np_rot90(
                np_array([teams, np_zeros(num_teams), np_zeros(num_teams), np_zeros(num_teams)], np_object))[::-1]
        self.stats = combined

    def __init_teams(self):
        self.teams = np_array([[int(team['team_number']), team['nickname'], team['locality'], team['region'],
                                team['country_name'], team['rookie_year']] for team in self.raw_teams], np_object)

    def __init_event(self):
        raw = self.raw_event
        self.event_info = np_array([raw['short_name'], raw['event_type_string'], raw['location']])

    def __init_alliances(self):
        alliances = [[team[3:] for team in alliance['picks']] for alliance in self.raw_event['alliances']]
        alliances = np_array(alliances, np_int)
        numbers = np_vstack(np_arange(1, 9, 1))
        self.alliances = np_concatenate((numbers, alliances), 1)

    def __init_awards(self):
        awards = []
        for award in self.raw_awards:
            recipients = award['recipient_list']
            if (len(recipients) is 1) and (recipients[0]['team_number'] is not None) \
                    and (recipients[0]['awardee'] is None):
                awards.append([award['name'], recipients[0]['team_number'], recipients[0]['team_number']])

            elif (len(recipients) is 1) and (recipients[0]['awardee'] is not None):
                awards.append([award['name'], recipients[0]['awardee'], recipients[0]['team_number']])

            elif len(recipients) > 1:
                for awardee in recipients:
                    if (awardee['team_number'] is not None) and (awardee['awardee'] is None):
                        awards.append([award['name'], awardee['team_number'], awardee['team_number']])

                    elif awardee['awardee'] is not None:
                        awards.append([award['name'], awardee['awardee'], awardee['team_number']])

        self.awards = np.array(awards)

    def __check_team(self, team):
        if team in self.get_team()[:, 0]:
            return True
        else:
            # TODO add event name
            print('Team %i is not in the %s' % (team, 'event'))
            return False

    def update_data(self):
        """Update all of the Event's data from TheBlueAlliance, requires internet connection."""
        self.qualification_matches = []
        self.quarter_final_matches = []
        self.semi_final_matches = []
        self.final_matches = []

        self.raw_event = self._pull_request(self.URL + 'event/' + self.EVENT_KEY)
        self.raw_teams = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/teams')
        self.raw_matches = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/matches')
        self.raw_rankings = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/rankings')
        self.raw_stats = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/stats')
        self.raw_awards = self._pull_request(self.URL + 'event/' + self.EVENT_KEY + '/awards')

        self.__init_matches()
        self.__init_statistics()
        self.__init_rankings()
        self.__init_teams()
        self.__init_event()
        self.__init_alliances()
        self.__init_awards()

    def change_event(self, event_key):
        """Change event from one to another

        Keyword arguments:
        event_key (str) -- The event key of new event"""
        self.EVENT_KEY = event_key
        self.update_data()

    @staticmethod
    def __count_matches(matches, match_type='qm'):
        match_sum = 0
        for match in matches:
            if match['comp_level'] == match_type:
                match_sum += 1
        return match_sum

    def get_matches(self, team_number='all', match_type='qm'):
        """Retrieve matches from the event

        Keyword arguments:
        team_number -- if an int, retrieves matches played by that team.
                        If 'all', then it retrieves all matches (default 'all')
        match_type (str) -- from which type of matches to choose from: 'qm', 'qf', 'sf', 'f'. (default 'qm')

        Returns:
        numpy array -- [type, match_number, Red_alliance, Blue_alliance, Red_score, Blue_score, Winner, Match_ID]
                                    Two dimensional if team number was 'all'
        """
        if team_number is 'all':
            if match_type is 'qm':
                return self.qualification_matches
            elif match_type is 'qf':
                return self.quarter_final_matches
            elif match_type is 'sf':
                return self.semi_final_matches
            elif match_type is 'f':
                return self.final_matches

        else:
            if not self.__check_team(team_number):
                return []

            matches = self.get_matches('all', match_type)

            if len(matches) is not 0:
                team_matches = [((team_number in match[2]) or (team_number in match[3])) for match in matches[:, :4]]
                team_matches = np_array(team_matches)
                team_matches = matches[team_matches]
            else:
                team_matches = []

            return team_matches

    def get_team(self, team_number='all'):
        """Retrieve infromation about teams at the event

        Keyword arguments:
        team_number -- if an int, retrieves information on that team.
                        If 'all', then it retrieves all teams (default 'all')

        Returns: [Team_Number, Team_Name, City, State, Country, Creation_Year]
                                    Two dimensional if team number was 'all'

        """

        if team_number is 'all':
            return self.teams

        if not self.__check_team(team_number):
            return []

        return self.teams[self.teams[:, 0] == team_number][0]

    def get_rankings(self, team_number='all'):
        """Retrieves ranking from the event

        Keyword arguments:
        team_number -- if an int, retrieves rankings of that team.
                        If 'all', then it retrieves all teams (default 'all')

        Returns:
        numpy array -- [Rank, Team_Number, Qual_Average, Auto, Container, Coopertition, Litter, Tote, Matched_Played]
                                    Two dimensional if team number was 'all'
        """

        # ['Rank', 'Team', 'Qual Avg', 'Auto', 'Container', 'Coopertition', 'Litter', 'Tote', 'Played']
        if team_number is 'all':
            return self.rankings

        if not self.__check_team(team_number):
            return []

        curr_rankings = self.rankings[self.rankings[:, 1] == team_number]
        if len(curr_rankings) is not 0:
            return curr_rankings[0]
        return []

    def get_statistics(self, team_number='all'):
        """Retrieves statistics about teams at the event

        Keyword arguments:
        team_number -- if an int, retrieves statistics of that team.
                        If 'all', then it retrieves all teams (default 'all')

        Returns:
        numpy array -- [Team_Number, OPR, DPR, CCWM]
                                    Two dimensional if team number was 'all'
        """
        if team_number is 'all':
            return self.stats

        if not self.__check_team(team_number):
            return []

        curr_stats = self.stats[self.stats[:, 0] == team_number]
        if len(curr_stats) is not 0:
            return curr_stats[0]
        return np_array([team_number, 0, 0, 0])

    def get_alliance(self, number='all'):
        """Retrieves ranking from the event

        Keyword arguments:
        number -- if an int, the retrieves that ranked alliance.
                        If 'all', then it retrieves all alliances (default 'all')

        Returns: ]
        numpy array -- [Rank, First Team, Second Team, Third Team]
                                    Two dimensional if team number was 'all'
        """
        if number is 'all':
            return self.alliances

        if number > 8 or number < 1:
            print('Invalid Alliance Number (Must be between 1 and 8) : %i' % number)
            return

        return self.alliances[number - 1]

    def get_event_info(self):
        """Retrieves info about the current Event

        Returns:
        numpy array -- [Name, Type, Location]
        """
        return self.event_info

    def get_awards(self):
        """Retrieves awards given at the regional

        Returns:
        2d numpy array -- [[Award, Winner, Associated_Team]]"""
        return self.awards


def get_events_and_codes(year=2015, search_term = 'all'):
    """Function to provide with Event names and codes
    year (int) -- Year the event took place in
    search_term (str) -- narrow down list of events by searching for your event name ex. 'Silicon Valley' (default 'all') """

    year = str(year)
    request = REQUEST.Request('http://www.thebluealliance.com/api/v2/events/%s' % year)
    request.add_header('X-TBA-App-Id', '%s:%s:%s' % ('event_getter', 'blue_alliance_python_api', '1.1'))
    response = REQUEST.urlopen(request)
    response = json.loads(response.read().decode("utf-8"))

    events = np_array([[event['short_name'], event['key']] for event in response])
    ind = np.lexsort((events[:, 1], events[:, 0]))

    events = events[ind]

    if search_term is 'all':
        return events
    else:
        curr = events[events[:, 0] == search_term]
        if len(curr) is 0:
            print('no such event found, remember to capitalize the first letter')
            return
        return curr[0]



def load_database(path):
    """Load an Event object from a path

    Keyword Arguments:
    path (str) -- Path to saved database file"""
    return load(path)