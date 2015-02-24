from .controller import Controller

class DDS220(Controller):
  """
  A controller for a DDS220 stage.
  """
  def __init__(self, connection, stage_num):
    super(DDS220, self).__init__(connection=connection, dest=0x21 + stage_num)

    self.max_velocity = 300
    self.max_acceleration = 5000

    enccnt = 20000
    T = 102.4 * 1e-6

    # these equations are taken from the APT protocol manual
    self.position_scale = enccnt
    self.velocity_scale = enccnt * T * 65536
    self.acceleration_scale = enccnt * T * T * 65536

    self.linear_range = (0,220)
