 #!/bin/bash
 #You need lingua and gettext installed to run this
 
 echo "Updating Arche.pot"
 pot-create -d Arche -o arche/locale/Arche.pot arche/.
 echo "Merging Swedish localisation"
 msgmerge --update  arche/locale/sv/LC_MESSAGES/Arche.po  arche/locale/Arche.pot
 echo "Updated locale files"
 
 