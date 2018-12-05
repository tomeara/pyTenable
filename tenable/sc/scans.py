'''
scans
=====

NOTE: not currently tested code.

The following methods allow for interaction into the Tenable.sc 
`Scan <https://docs.tenable.com/sccv/api/Scan.html>`_ API.  While the api 
endpoints obliquely refers to the model in which this collection of actions
modifies as "Scans", Tenable.sc is actually refering to the scan *definitions*,
which are the un-launched and/or scheduled scans typically seen within the
**Active Scans** section within Tenable.sc.

Methods available on ``sc.scans``:

.. rst-class:: hide-signature
.. autoclass:: ScanAPI

    .. automethod:: copy
    .. automethod:: create
    .. automethod:: delete
    .. automethod:: details
    .. automethod:: launch
    .. automethod:: list
    .. automethod:: update

.. iCal Date-Time:
    https://tools.ietf.org/html/rfc5545#section-3.3.5
.. iCal Recurrance Rule:
    https://tools.ietf.org/html/rfc5545#section-3.3.10
'''
from .base import SCEndpoint
from tenable.utils import dict_merge
from tenable.errors import UnexpectedValueError

class ScanAPI(SCEndpoint):
    def _constructor(self, **kw):
        '''
        Handles parsing the keywords and returns a scan definition document
        '''
        if 'name' in kw:
            # simply verify that the name attribute is a string.
            self._check('name', kw['name'], str)

        if 'type' in kw:
            # If the scan type is manually specified, then we will want to make
            # sure that its a valid input.
            self._check('type', kw['type'], str, choices=['plugin', 'policy'])

        if 'description' in kw:
            # The description should always be a string value.
            self._check('description', kw['description'], str)

        if 'repo' in kw:
            # as we accept input as a integer, we need to expand the repository
            # attribute to be a dictionary item with just the ID (per API docs)
            kw['repository'] = {'id': self._check(
                'repo', kw['repo'], int)}

        if 'scan_zone' in kw:
            # similarly to the repository, the API expects the zone to be
            # defined as a sub-dictionary with just the id field.
            kw['zone'] = {'id': self._check(
                'scan_zone', kw['scan_zone'], int, default=0)}
            del(kw['scan_zone'])

        if 'email_complete' in kw:
            # As emailOnFinish is effectively a string interpretation of a bool
            # value, if the snake case equivilent is used, we will convert it
            # into the expected paramater and remove the snake cased version.
            kw['emailOnFinish'] = str(self._check(
                'email_complete', kw['email_complete'], bool, default=False)).lower()
            del(kw['email_complete'])

        if 'email_launch' in kw:
            # As emailOnLaunch is effectively a string interpretation of a bool
            # value, if the snake case equivilent is used, we will convert it
            # into the expected paramater and remove the snake cased version.
            kw['emailOnLaunch'] = str(self._check(
                'email_launch', kw['email_launch'], bool, default=False)).lower()
            del(kw['email_launch'])

        if 'timeout' in kw:
            # timeout is the checked version of timeoutAction.  If timeout is
            # specified, we will check to make sure that the action is a valid
            # one, put the result into timeoutAction, and remove timeout.
            kw['timeoutAction'] = self._check('timeout', kw['timeout'], str, 
                choices=['discard', 'import', 'rollover'], default='import')
            del(kw['timeout'])

        if 'vhosts' in kw:
            # As scanningVirtualHosts is effectively a string interpretation of 
            # a bool value, if the snake case equivilent is used, we will 
            # convert it into the expected paramater and remove the snake cased
            # version.
            kw['scanningVirtualHosts'] = str(self._check(
                'vhosts', kw['vhosts'], bool, default=False)).lower()
            del(kw['vhosts'])

        if 'rollover' in kw:
            # The scan rolloverType parameter simply shortened to better conform
            # to pythonic naming convention.
            kw['rolloverType'] = self._check('rollover', kw['rollover'], str,
                choices=['nextDay', 'template'], default='template')
            del(kw['rollover'])

        if 'targets' in kw:
            # targets is list representation of a comma-seperated string of
            # values for the ipList attribute.  By handling as a list instead of
            # the raw string varient the API expects, we can ensure that there
            # isn't any oddities, such as extra spaces, between the commas.
            kw['ipList'] = ','.join([self._check('target', i.strip(), str) 
                for i in self._check('targets', kw['targets'], list)])
            del(kw['targets'])

        if 'max_time' in kw:
            # maxScanTime is a integer encased in a string value.  the snake
            # cased version of that expects an integer and converts it into the
            # string equivilent.
            kw['maxScanTime'] = str(self._check('max_time', kw['max_time'], int))
            del(kw['max_time'])

        if 'auto_mitigation' in kw:
            # As classifyMitigatedAge is effectively a string interpretation of 
            # an int value, if the snake case equivilent is used, we will 
            # convert it into the expected paramater and remove the snake cased
            # version.
            kw['classifyMitigatedAge'] = str(self._check(
                'auto_mitigation', kw['auto_mitigation'], int, default=0))
            del(kw['auto_mitigation'])

        # hand off the building the schedule sub-document to the schedule 
        # document builder.
        kw = self._schedule_document_creator(kw)

        if 'reports' in kw:
            # as the reports list should already be in a format that the API
            # expects, we will simply verify that everything looks like it should.
            for item in self._check('reports', kw['reports'], list):
                self._check('report:id', item['id'], int),
                self._check('reportSource', item['reportSource'], str, choices=[
                    'cumulative', 
                    'patched', 
                    'individual', 
                    'lce', 
                    'archive', 
                    'mobile'
                ])

        if 'asset_lists' in kw:
            # asset_lists is the collapsed list of id documents that the API
            # expects to see.  We will check each item in the list to make sure
            # its in the right type and then expand it into a subdocument.
            kw['assets'] = [{'id': self._check('asset_list:id', i, int)} 
                for i in self._check('assets_lists', kw['asset_lists'], list)]
            del(kw['asset_lists'])

        if 'creds' in kw:
            # creds is the collapsed list of id documents that the API expects 
            # to see.  We will check each item in the list to make sure its in 
            # the right type and then expand it into a subdocument.
            kw['credentials'] = [{'id': self._check('cred:id', i, int)} 
                for i in self._check('creds', kw['creds'], list)]
            del(kw['creds'])

        # Lastly, we need to handle the scan types automatically...
        if 'plugin_id' in kw and 'policy_id' in kw:
            # if both are specified, something is wrong here and we should throw
            # an exception.
            raise UnexpectedValueError(
                'specify either a plugin_id or a policy_id for a scan, not both.')
        
        elif 'plugin_id' in kw:
            # If just the plugin_id is specified, then we are safe to assume
            # that this is a plugin-based scan.  set the pluginID attribute as
            # the API would expect and remove the snake cased varient that was
            # inputted.
            kw['type'] = 'plugin'
            kw['pluginID'] = self._check('plugin_id', kw['plugin_id'], int)
            del(kw['plugin_id'])

        elif 'policy_id' in kw:
            # If just the policy_id is specified, then we are safe to assume
            # that this is a policy-based scan.  set the policy id attribute 
            # within the policy document as the API would expect and remove the 
            # snake cased varient that was inputted.
            kw['type'] = 'policy'
            kw['policy'] = {'id': self._check('policy_id', kw['policy_id'], int)}
            del(kw['policy_id'])

        return kw

    def list(self, fields=None):
        '''
        Retreives the list of scan definitions.

        + `SC Scan List <https://docs.tenable.com/sccv/api/Scan.html#scan_GET>`_

        Args:
            fields (list, optional): 
                A list of attributes to return for each scan.

        Returns:
            list: A list of scan resources.

        Examples:
            >>> for scan in sc.scans.list():
            ...     pprint(scan)
        '''
        params = dict()
        if fields:
            params['fields'] = ','.join([self._check('field', f, str) 
                for f in fields])

        return self._api.get('scan', params=params).json()['response']

    def create(self, name, repo, **kw):
        '''
        Creates a scan definition.

        + `SC Scan Create <https://docs.tenable.com/sccv/api/Scan.html#scan_POST>`_

        Args:
            name (str): The name of the scan.
            repo (int):
                The repository id for the scan.
            auto_mitigation (int, optional):
                How many days to hold on to data before mitigating it?  The 
                default value is 0.
            asset_lists (list, optional):
                A list of asset list ids to run the scan against.  A logical OR
                will be performed to comupute what hosts to scan against.
            credential_ids (list, optional):
                A list of credential ids to use for tue purposes of this scan.
                This list should be treated as an un-ordered list of credentials.
            description (str, optional): A description for the scan.
            email_complete (bool, optional):
                Should we notify the owner upon completion of the scan?  The
                default is ``False``.
            email_launch (bool, optional):
                Should we notify the owner upon launching the scan?  The default
                is ``False``.
            host_tracking (bool, optional):
                Should DHCP host tracking be enabled?  The default is False.
            max_time (int, optional):
                The maximum amount of time that the scan may run in seconds.
                The default is ``3600`` seconds.
            policy_id (int, optional): 
                The policy id to use for a policy-based scan.
            plugin_id (int, optional):
                The plugin id to use for a plugin-based scan.
            reports (list, optional):
                What reports should be run upon completion of the scan?  Each
                report dictionary requires an id for the report definition and
                the source for which to run the report against.  Example:
                ``{'id': 1, 'reportSource': 'individual'}``.
            rollover (str, optional):
                How should rollover scans be created (assuming the scan is 
                configured to create a rollover scan with the timeout action).
                The available actions are to automatically start the ``nextDay``
                at the same time the scan was originally configured to run, and
                to generate a rollover ``template``.  The default action is to
                generate a ``template``.
            scan_zone (int, optional):
                The zone identifier to use for the scan.  If non is selected
                then the default of "0" or "All Zones" is selected.
            schedule_type (str, optional):
                What type of scan schedule shall this be?  Available supported
                values are ``dependent``, ``ical``, ``never``, ``rollover``, and
                ``template``.  The default value if unspecified is ``never``.
            schedule_start (str, optional):
                The time in which the trigger should start firing.  This value
                must conform to the `iCal Date-Time`_ standard.  Further this
                parameter is only required when specifying the schedule_type as
                ``ical``.
            schedule_repeat (str, optional):
                The rule that dictates the frequency and timing that the alert
                will run.  This value must conform to the `iCal Recurrance Rule`_
                format.  Further this parameter is only required when specifying
                the schedule_type as ``ical``.
            targets (list, optional):
                A list of valid targets.  These targets could be IPs, FQDNs,
                CIDRs, or IP ranges.
            timeout (str, optional):
                How should an incomplete scan be handled?  The available actions
                are ``discard``, ``import``, and ``rollover``.  The default
                action is ``import``.
            vhosts (bool, optional):
                Should virtual host logic be enabled for the scan?  The default
                is ``False``.
        
        Returns:
            dict: The scan resource for the created scan.

        Examples:
            Creating a scan for a single host:

            >>> sc.scans.create('Example scan', 1, policy_id=1001,
            ...     targets=['127.0.0.1'])
        '''
        kw['name'] = name
        kw['repo'] = repo
        scan = self._constructor(**kw)
        return self._api.post('scan', json=scan).json()['response']

    def details(self, id, fields=None):
        '''
        Returns the details for a specific scan.

        + `SC Scan Details <https://docs.tenable.com/sccv/api/Scan.html#ScanRESTReference-/scan/{id}>`_

        Args:
            id (int): The identifier for the scan.
            fields (list, optional): A list of attributes to return.

        Returns:
            dict: The alert resource record.

        Examples:
            >>> alert = sc.alerts.detail(1)
            >>> pprint(alert)
        '''
        params = dict()
        if fields:
            params['fields'] = ','.join([self._check('field', f, str) for f in fields])

        return self._api.get('scan/{}'.format(self._check('id', id, int)),
            params=params).json()['response']

    def update(self, id, **kw):
        '''
        Updates an existing scan definition.

        + `SC Scan Update <https://docs.tenable.com/sccv/api/Scan.html#scan_id_PATCH>`_

        Args:
            id (int): The identifier for the scan.
            auto_mitigation (int, optional):
                How many days to hold on to data before mitigating it?
            asset_lists (list, optional):
                A list of asset list ids to run the scan against.  A logical OR
                will be performed to comupute what hosts to scan against.
            creds (list, optional):
                A list of credential ids to use for tue purposes of this scan.
                This list should be treated as an un-ordered list of credentials.
            description (str, optional): A description for the scan.
            email_complete (bool, optional):
                Should we notify the owner upon completion of the scan?
            email_launch (bool, optional):
                Should we notify the owner upon launching the scan?
            host_tracking (bool, optional):
                Should DHCP host tracking be enabled?
            max_time (int, optional):
                The maximum amount of time that the scan may run in seconds.
            name (str, optional): The name of the scan.
            policy (int, optional): 
                The policy id to use for a policy-based scan.
            plugin (int, optional):
                The plugin id to use for a plugin-based scan.
            reports (list, optional):
                What reports should be run upon completion of the scan?  Each
                report dictionary requires an id for the report definition and
                the source for which to run the report against.  Example:
                ``{'id': 1, 'reportSource': 'individual'}``.
            repo (int, optional):
                The repository id for the scan.
            rollover (str, optional):
                How should rollover scans be created (assuming the scan is 
                configured to create a rollover scan with the timeout action).
                The available actions are to automatically start the ``nextDay``
                at the same time the scan was originally configured to run, and
                to generate a rollover ``template``.
            scan_zone (int, optional):
                The zone identifier to use for the scan.
            schedule_type (str, optional):
                What type of scan schedule shall this be?  Available supported
                values are ``dependent``, ``ical``, ``never``, ``rollover``, and
                ``template``.
            schedule_start (str, optional):
                The time in which the trigger should start firing.  This value
                must conform to the `iCal Date-Time`_ standard.  Further this
                parameter is only required when specifying the schedule_type as
                ``ical``.
            schedule_repeat (str, optional):
                The rule that dictates the frequency and timing that the alert
                will run.  This value must conform to the `iCal Recurrance Rule`_
                format.  Further this parameter is only required when specifying
                the schedule_type as ``ical``.
            targets (list, optional):
                A list of valid targets.  These targets could be IPs, FQDNs,
                CIDRs, or IP ranges.
            timeout (str, optional):
                How should an incomplete scan be handled?  The available actions
                are ``discard``, ``import``, and ``rollover``.
            vhosts (bool, optional):
                Should virtual host logic be enabled for the scan?
        
        Returns:
            dict: The scan resource for the created scan.

        Examples:
            Creating a scan for a single host:

            >>> sc.scans.update(1, name='Example scan')
        '''
        scan = self._constructor(**kw)
        return self._api.patch('scan/{}'.format(self._check('id', id, int)), 
            json=scan).json()['response']

    def delete(self, id):
        '''
        Removes the specified scan from SecurityCenter.

        + `SC Scan Delete <https://docs.tenable.com/sccv/api/Scan.html#scan_id_DELETE>`_

        Args:
            id (int): The identifier for the scan to delete.

        Returns:
            list: The list of scan id removed.

        Examples:
            >>> sc.scans.delete(1)
        '''
        return self._api.delete('scan/{}'.format(self._check('id', id, int))
            ).json()['response']['scans']

    def copy(self, id, name=None, user_id=None):
        '''
        Copies an existing scan definition.

        + `SC Scan Copy <https://docs.tenable.com/sccv/api/Scan.html#ScanRESTReference-/scan/{id}/copyScanCopyPOST1>`_

        Args:
            id (int): The scan definition identifier to copy.
            name (str, optional): The name of the copy thats created.
            user_id (int, optional): 
                The user id to assign as the owner of the new scan definition.

        Returns:
            dict: Scan definition resource.

        Examples:
            >>> sc.scans.copy(1, name='Cloned Scan')
        '''
        payload = dict()
        if name:
            payload['name'] = self._check('name', name, str)
        if user_id:
            payload['targetUser'] = {'id': self._check('user_id', user_id, int)}

        return self._api.post('scan/{}/copy'.format(
            self._check('id', id, int)), json=payload).json()['response']['scan']

    def launch(self, id, diagnostic_target=None, diagnostic_password=None):
        '''
        Launches a scan definition.

        + `SC Scan <https://docs.tenable.com/sccv/api/Scan.html#ScanRESTReference-/scan/{id}/launch>`_

        Args:
            id (int): The scan definition identifier to launch.
            diagnostic_target (str, optional):
                A valid IP or hostname to launch a diagnostic scan against.  The
                ``diagnostic_password`` must also be specified or else this
                parameter will be ignored.
            diagnostic_password (str, optional):
                A password to use for the diagnostic scan.  The
                ``diagnostic_target`` must also be specified or else this
                parameter will be ignored.

        Returns:
            dict: A scan result resource for the newly launched scan.

        Examples:
            >>> running = sc.scans.launch(1)
            >>> print('The Scan Result ID is {}'.format(
            ...     running['scanResult']['id']))
        '''
        payload = dict()
        if diagnostic_target and diagnostic_passwsord:
            payload['diagnosticTarget'] = self._check(
                'diagnostic_target', diagnostic_target, str)
            payload['diagnosticPassword'] = self._check(
                'diagnostic_password', diagnostic_password, str)

        return self._api.post('scan/{}/launch'.format(
            self._check('id', id, int)), json=payload).json()['response']