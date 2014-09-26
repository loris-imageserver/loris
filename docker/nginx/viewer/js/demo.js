var SERVER = 'http://' + window.location.host + '/iiif/';
var INFO = '/info.json';

var SAMPLES = [
  '67352ccc-d1b0-11e1-89ae-279075081939.jp2',
  'sul_precincts.jp2',
  '01%2F02%2F0001.jp2',
  '01%2F02%2Fgray.jp2',
  '01%2F03%2F0001.jpg',
  '01%2F04%2F0001.tif'
];

var height = jQuery(window).height();
var width = jQuery(window).width();

$('#viewer').width( width );
$('#viewer').height( height );
$('#container').width( width );
$('#container').height( height );
$('.toolbar').width( width );

// Read a page's GET URL variables and return them as an associative array.
function getUrlVars() {
  var vars = [], hash;
  var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
  for(var i = 0; i < hashes.length; i++) {
    hash = hashes[i].split('=');
    vars.push(hash[0]);
    vars[hash[0]] = hash[1];
  }
  return vars;
}

var osd_config = {
  id: "viewer",
  prefixUrl: "js/openseadragon/images/",
  preserveViewport: true,
  showNavigator:  true,
  visibilityRatio: 1,
  minZoomLevel: 1,
  tileSources: []
};


feedMe = getUrlVars()['feedme'];

if (feedMe) {
  osd_config['tileSources'].push(SERVER + feedMe + INFO);
} else {
  for (c=0; c<SAMPLES.length; c++) {
    osd_config['tileSources'].push(SERVER + SAMPLES[c] + INFO);
  }
}

OpenSeadragon(osd_config);
