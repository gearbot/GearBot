export function getCookie(cookieName: string) {
    let b = document.cookie.match('(^|;)\\s*' + cookieName + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}