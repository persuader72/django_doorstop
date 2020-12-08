let alreadyInit = false;

$(document).ready(function() {
  if(alreadyInit) return;
  alreadyInit = true;

  $.each($('.easymde-box'), function(i, elem) {
    let options = {};
    let attrstring = $(elem).attr('data-easymde-options');
    if(attrstring) options = JSON.parse(attrstring);
    options['element'] = elem;
    console.log(options)
    let easymde = new EasyMDE(options);
    elem.EasyMDE = easymde;
  });
});
