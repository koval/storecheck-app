$(document).ready(function(){
 // Set up a listener so that when anything with a class of 'tab' 
 // is clicked, this function is run.
 $('.htab').click(function (e) {

  // Remove the 'active' class from the active tab.
  $('#htabs_container > .htabs > li.hactive')
          .removeClass('hactive');

  // Add the 'active' class to the clicked tab.
  $(this).parent().addClass('hactive');

  // Remove the 'tab_contents_active' class from the visible tab contents.
  $('#htabs_container > .htab_contents_container > div.htab_contents_active')
          .removeClass('htab_contents_active');

  // Add the 'tab_contents_active' class to the associated tab contents.
  $(this.rel).addClass('htab_contents_active');
  e.preventDefault();
 });

 $('#refrigerators .vtab').click(function (e) {

  // Remove the 'active' class from the active tab.
  $('#refrigerators #vtabs_container > .vtabs > li.vactive')
          .removeClass('vactive');

  // Add the 'active' class to the clicked tab.
  $(this).parent().addClass('vactive');

  // Remove the 'tab_contents_active' class from the visible tab contents.
  $('#refrigerators #vtabs_container > .vtab_contents_container > div.vtab_contents_active')
          .removeClass('vtab_contents_active');

  // Add the 'tab_contents_active' class to the associated tab contents.
  $(this.rel).addClass('vtab_contents_active');
  e.preventDefault();
 });

 $('#store .vtab').click(function (e) {

  // Remove the 'active' class from the active tab.
  $('#store #vtabs_container > .vtabs > li.vactive')
          .removeClass('vactive');

  // Add the 'active' class to the clicked tab.
  $(this).parent().addClass('vactive');

  // Remove the 'tab_contents_active' class from the visible tab contents.
  $('#store #vtabs_container > .vtab_contents_container > div.vtab_contents_active')
          .removeClass('vtab_contents_active');

  // Add the 'tab_contents_active' class to the associated tab contents.
  $(this.rel).addClass('vtab_contents_active');
  e.preventDefault();
 });

  function hideInputs(id) {
    // hide inputs
    var inputs = $('#' + id + ' input');
    for (var i=0; i<inputs.length; i++) {
      var elem = $(inputs[i]);
      var type_ = elem.attr('type');
      if (type_ == 'submit') {
        // skip submit control
        continue
      } else if (type_ == 'hidden') {
        // and hidden fields
        continue
      } else if (type_ == 'checkbox') {
        elem.attr('disabled', 'disabled');
      } else {
        var new_elem = $('<span>' + elem.val() + '</span>');
        elem.hide();
        elem.parent().append(new_elem);
      }
    }

    // hide select
    var selects = $('#' + id + ' select');
    for (var i=0; i<selects.length; i++) {
      var elem = $(selects[i]);
      var opts = elem.children();
      var val;
      for (var j=0; j<opts.length; j++) {
        var opt = $(opts[j]);
        if (opt.attr('selected')) {
          val = opt.text();
          break;
        }
      }
      var new_elem = $('<span>'+val+'</span>');
      elem.hide();
      elem.parent().append(new_elem);
    }

    return false;
  }

  // hide all form inputs
  hideInputs('refrigerators');
  hideInputs('store');

  $('input[name="change"]').click(function (e) {
    // show all input fields
    var id = $(this).closest('div.vtab_contents').attr('id');
    $('#'+id+' span').hide();
    $('#'+id+' input').show().removeAttr('disabled');
    $('#'+id+' select').show().removeAttr('disabled');

    // and disable future clicks
    $(this).attr('disabled', 'disabled');

    return false;
  });

  // submitting a refrigerator form
  $('#refrigerators input[name="confirm"]').click(function (e) {
    form = $(this).closest('form');
    form.ajaxSubmit(function(responseText, statusText) { 
      if (responseText.indexOf('http://') === 0) {
        form.find('input[name="confirm"]').attr('disabled', 'disabled');
        var current_id = form.closest('.vtab_contents').attr('id');
        var current_tab = $('.vtab[rel="#'+current_id+'"]');
        current_tab.parent().addClass('done');
        var next_tab = current_tab.parent().next();
        if (next_tab.length > 0) {
          // go to next refrigerator
          next_tab.children('a.vtab').click();
        } else {
          // go to store
          $('a.htab[rel="#store"]').click()
        }
      } else {
        form.children('table').html(responseText);
        form.find('input[name="confirm"]').removeAttr('disabled');
      }
    });
    return false;
  });

  //submitting a store form
  $('#store input[name="confirm"]').click(function (e) {
    form = $(this).closest('form');
    form.ajaxSubmit(function(responseText, statusText) { 
      if (responseText.indexOf('http://') === 0) {
        // load new pad
        window.location = responseText;
      } else {
        form.children('table').html(responseText);
        form.find('input[name="confirm"]').removeAttr('disabled');
      }
    });
    return false;
  });

});
