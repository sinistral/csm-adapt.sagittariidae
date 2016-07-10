
class NotFound(Exception):
    status_code = 404

    def __init__(self, res_type, res_name):
        self.message = 'The {type:} "{name:}" could not be found.'.format(
            type=res_type, name=res_name)

    def to_dict(self):
        return {'message': self.message}
