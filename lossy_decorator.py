import logging

import numpy as np

from helpers import get_stdout_logger
from senders.udt_sender import UDTSender

logger = get_stdout_logger('lossy decorator')

def get_lossy_udt_sender(loss_prob):

    def get_decision():
        return np.random.choice(['lost', 'sent'], p=[loss_prob, 1 - loss_prob])

    class LossyUDTSender:
        """
        This is udt sender that losses packets with probability loss_prob
        """
        def __init__(self,*args, **kwargs):
            self.sender = UDTSender(*args, *kwargs)
            self.loss_prob = loss_prob

        def send_data(self, data_chunk, seq_number):
            if get_decision() == 'sent':
                self.sender.send_data(data_chunk, seq_number)


        def send_ack(self, seq_number):
            if get_decision() == 'sent':
                self.sender.send_ack(seq_number)
            else:
                logger.log(logging.INFO, 'ack got lost')


        def __getattribute__(self, attr):
            """
            this is called whenever any attribute of a LossyUDTSender object is accessed. This function first tries to
            get the attribute off LossyUDTSender. If it fails then it tries to fetch the attribute from self.oInstance (an
            instance of the decorated class). If it manages to fetch the attribute from self.oInstance, and
            the attribute is an instance method then `time_this` is applied.
            """
            try:
                found_attr = super(LossyUDTSender, self).__getattribute__(attr)
            except AttributeError:
                pass
            else:
                return found_attr

            found_attr = self.sender.__getattribute__(attr)

            return found_attr


    return LossyUDTSender

def make_lossy_sender(sender, loss_prob):
    """
    use this to make lossy senders and if u want receivers to lose acks
    use the lossy udt sender above to make lossy udt_senders and use those to send the acks,
    the above maker is called as LossyUDT(loss_prop)(server_ip, server_port)
    -- see stop and wait receiver for an example
    :param sender:
    :param loss_prob:
    :return:
    """


    sender.udt_sender_class = get_lossy_udt_sender(loss_prob)
    sender.setup_senders_and_receivers()
    return sender
