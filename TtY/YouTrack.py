from datetime import datetime
import requests


class YouTrack:
    def __init__(self, youtrack_login, youtrack_password, youtrack_link, youtrack_project,
                 youtrack_subsystem=None):
        self.youtrack_login = youtrack_login
        self.youtrack_password = youtrack_password
        self.youtrack_link = youtrack_link
        self.youtrack_project = youtrack_project
        self.youtrack_subsystem = youtrack_subsystem

    def import_issues(self, trello_cards, mapping_dict, number_in_project, attachments=False):
        xml_string = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        xml_string += '<issues>\n'
        issues_strings, attachments_dict = self._issues_string(trello_cards, mapping_dict, attachments,
                                                               number_in_project)
        xml_string += issues_strings
        xml_string += '</issues>'

        import_url = '%s/rest/import/%s/issues' % (self.youtrack_link, self.youtrack_project)
        headers = {'Content-Type': 'application/xml'}

        response = requests.put(import_url, auth=(self.youtrack_login, self.youtrack_password),
                                headers=headers, data=xml_string.decode('utf-8'))
        self._import_attachments(attachments_dict)

    def _issues_string(self, trello_cards, mapping_dict, attachments, number_in_project):
        issue_string = '\n'
        attachments_dict = dict()
        for card in trello_cards:
            issue_string += '<issue>\n'
            issue_string += self._get_issue_fields(mapping_dict, card, number_in_project)
            issue_string += '</issue>\n'
            if attachments:
                card_attachments = []
                for attachment in card["attachments"]:
                    response = requests.get(attachment["url"])
                    card_attachments.append((attachment["name"], response.content))
                if card_attachments:
                    attachments_dict[self.youtrack_project + '-' + unicode(number_in_project)] \
                        = card_attachments
            number_in_project += 1
        return issue_string, attachments_dict

    def _import_attachments(self, attachments_dict):
        for issue_name in attachments_dict.keys():
            files_data = attachments_dict[issue_name]
            for file_data in files_data:
                response = requests.post(self.youtrack_link + "/rest/import/%s/attachment"
                                                              "?authorLogin=%s&created=%s" %
                                         (issue_name, self.youtrack_login, self._time_now()),
                                         files={'file': file_data},
                                         auth=(self.youtrack_login, self.youtrack_password))

    def _get_issue_fields(self, mapping_dict, card, number_in_project):
        fields = ''
        fields += self._field_string('created', self._time_now()) + '\n'
        fields += self._field_string('reporterName', self.youtrack_login) + '\n'
        fields += self._field_string('numberInProject', number_in_project) + '\n'
        for mapping_key in mapping_dict.keys():
            mapping_value = mapping_dict[mapping_key]
            # TODO make sure that no trello. exist without being in the supported keys
            if 'trello.' in mapping_value:
                trello_key = mapping_value[len('trello.'):]
                fields += self._field_string(mapping_key[len('youtrack.'):], card[trello_key])

            elif type(mapping_value) is dict:
                for value in mapping_value.keys():
                    conditions_dict = mapping_value[value]
                    all_conditions_satisfied = True
                    for condition in conditions_dict.keys():
                        condition_value = conditions_dict[condition]
                        trello_condition_key = condition[len('trello.'):]
                        if card[trello_condition_key] != condition_value:
                            all_conditions_satisfied = False
                            break
                    if all_conditions_satisfied:
                        fields += self._field_string(mapping_key[len('youtrack.'):], value)
            else:
                fields += self._field_string(mapping_key[len('youtrack.'):], mapping_value)
            fields += '\n'
        if self.youtrack_subsystem:
            fields += self._field_string('subsystem', self.youtrack_subsystem) + '\n'
        return fields

    def _field_string(self, name, value):
        return ('<field name="%s">\n'
                '   <value>%s</value>\n'
                '</field>' % (name, value))

    def _time_now(self):
        return int(datetime.now().strftime("%s")) * 1000
