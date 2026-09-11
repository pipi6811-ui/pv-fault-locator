<?php
/**
 * 維運拍照 — 同源轉發
 *
 * 瀏覽器只准網頁存取「同一個網域＋同一個連接埠」的資源。拍照頁在 443，
 * 而 DSM 的 API 在 5000/5001，兩者跨連接埠，請求會被瀏覽器擋下。
 * 反向代理的自訂標頭是加在送往後端的請求上，無法解決。
 *
 * 這支程式與拍照頁同樣由 Web Station 在 443 提供，因此對瀏覽器而言是同源；
 * 它在 NAS 內部把請求轉給 DSM，再把結果原樣送回。
 *
 * 用法：proxy.php?_cgi=auth.cgi，其餘查詢參數原樣轉送。
 * 對外只開放照片上傳所需的三個端點，其餘一律拒絕。
 */

declare(strict_types=1);

const DSM_BASE = 'http://localhost:5000';
const ALLOWED  = ['auth.cgi', 'entry.cgi', 'query.cgi'];
const MAX_BODY = 64 * 1024 * 1024;

function refuse(int $code, string $why): never {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['success' => false, 'proxy_error' => $why], JSON_UNESCAPED_UNICODE);
    exit;
}

// 目標端點以查詢參數指定。不用 PATH_INFO，因為 Web Station 的 nginx
// 只把結尾是 .php 的網址交給 PHP，proxy.php/webapi/... 會被當成找不到的檔案。
$cgi = $_GET['_cgi'] ?? '';
if ($cgi === '') {
    refuse(400, '缺少 _cgi 參數。正確用法：本檔案網址後面接 ?_cgi=auth.cgi');
}
if (!in_array($cgi, ALLOWED, true)) {
    refuse(403, '這個端點未開放：' . $cgi);
}

// 其餘查詢參數原樣轉給 DSM（例如上傳用的 _sid）
$query = $_GET;
unset($query['_cgi']);
$target = DSM_BASE . '/webapi/' . $cgi;
if ($query !== []) {
    $target .= '?' . http_build_query($query);
}

$ch = curl_init($target);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HEADER         => false,
    CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_TIMEOUT        => 600,
    CURLOPT_FOLLOWLOCATION => false,
]);

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    // multipart（照片上傳）由 PHP 解析過，需依原欄位重建；
    // 其餘（如登入的表單編碼）直接原樣轉送。
    if (!empty($_FILES)) {
        $fields = $_POST;
        foreach ($_FILES as $name => $f) {
            if (($f['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
                refuse(400, '檔案上傳失敗，錯誤碼 ' . $f['error'] .
                    '（常見原因是 PHP 的上傳大小上限太小）');
            }
            $fields[$name] = new CURLFile(
                $f['tmp_name'],
                $f['type'] ?: 'application/octet-stream',
                $f['name']
            );
        }
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $fields);
    } else {
        $body = file_get_contents('php://input');
        if ($body === false) $body = '';
        if (strlen($body) > MAX_BODY) refuse(413, '內容過大');
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
        $ct = $_SERVER['CONTENT_TYPE'] ?? 'application/x-www-form-urlencoded';
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: ' . $ct]);
    }
}

$result = curl_exec($ch);
if ($result === false) {
    $err = curl_error($ch);
    curl_close($ch);
    refuse(502, '轉發到 DSM 失敗：' . $err .
        '（確認 DSM 的 HTTP 連接埠是 5000，若已改過請同步修改本檔案的 DSM_BASE）');
}
$status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
curl_close($ch);

http_response_code($status);
header('Content-Type: application/json; charset=utf-8');
echo $result;
