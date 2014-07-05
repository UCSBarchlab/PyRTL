# Abstract export class

class ExportBase(object):
  def import_from_block(self, block):
    raise NotImplementedError("Export base \"import_from_block()\" not implemented!")

  def dump(self, file):
    raise NotImplementedError("Export base \"dump()\" not implemented.")

