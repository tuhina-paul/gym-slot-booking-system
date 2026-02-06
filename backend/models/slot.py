class Slot:
    def __init__(self,slot_id,start_time,end_time):
        self.slot_id = slot_id
        self.start_time = start_time
        self.end_time = end_time
        self.booked_by = None

    def to_dict(self):
        return{
            "slot_id" : self.slot_id,
            "start_time" : self.start_time,
            "end_time" : self.end_time,
            "booked_by" : self.booked_by
        }