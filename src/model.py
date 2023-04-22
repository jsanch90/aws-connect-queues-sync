class QueueModel:
    def __init__(self, **kwargs) -> None:
        self.id = kwargs['QueueId']
        self.arn = kwargs['QueueArn']
        self.name = kwargs['Name']
        self.description = kwargs.get('Description')

        #Setting OutboundCallerConfig paramaters if exists
        if kwargs.get('OutboundCallerConfig') is not None:
            params = self._get_outbound_caller_config(kwargs.get('OutboundCallerConfig'))
            self.outbound_caller_config_caller_id_name = params.get('caller_id_name')
            self.outbound_caller_config_caller_id_number_id = params.get('caller_id_number_id')
            self.outbound_caller_config_caller_id_flow_id = params.get('caller_id_flow_id')
        else:
            self.outbound_caller_config_caller_id_name = None
            self.outbound_caller_config_caller_id_number_id = None
            self.outbound_caller_config_caller_id_flow_id = None
        
        self.hours_of_operation_id = kwargs.get('HoursOfOperationId')
        self.max_contacts = kwargs.get('MaxContacts')
        self.status = kwargs.get('Status')
    
    def _get_outbound_caller_config(self, outbound_caller_config):
        outbound_caller_config_dict = {
            'caller_id_name': outbound_caller_config.get('OutboundCallerIdName'),
            'caller_id_number_id': outbound_caller_config.get('OutboundCallerIdNumberId'),
            'caller_id_flow_id': outbound_caller_config.get('caller_id_flow_id')
        }

        return outbound_caller_config