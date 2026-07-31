all: *.png

# Post-process PyRTL screenshots with ImageMagick:
# * Strip metadata.
# * Trim any existing border.
# * Add a 15-pixel black border.
#
# This process is idempotent.
%.png: .FORCE
	mogrify -strip -trim -bordercolor black -border 15 $@

.FORCE:
