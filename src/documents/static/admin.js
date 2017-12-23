
function show_colors() {
    $('.field-colour select').each(function() {
        $(this).css('background-color', $('option:selected', this).text());
    });
}

$(function() {
    $('.field-colour select').on('change', show_colors);
    show_colors();
});
