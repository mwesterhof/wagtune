$(document).ready(() => {
    $('[data-abtest-hook]').on('click', (event) => {
        const hook = $(event.currentTarget).data('abtest-hook');
        const weight = $(event.currentTarget).data('abtest-weight');

        const token = $('#trackinginfo').data('abtest-token');
        const url = $('#trackinginfo').data('abtest-url');

        $.get(url, {hook: hook, token: token, weight: weight});
    });
});
