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
 * 端點不用 PATH_INFO：Web Station 的 nginx 只把結尾為 .php 的網址交給 PHP。
 * 對外只開放照片上傳所需的三個端點，其餘一律拒絕。
 *
 * 語法刻意維持在 PHP 7.0 可接受的範圍，避免 NAS 上的版本差異造成執行失敗。
 */

// 轉發目標。若 DSM 的 HTTP 連接埠不是 5000，改這一行。
define('DSM_BASE', 'http://localhost:5000');

$ALLOWED = array('auth.cgi', 'entry.cgi', 'query.cgi');

function refuse($code, $why) {
    if (!headers_sent()) {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
    }
    echo json_encode(
        array('success' => false, 'proxy_error' => $why),
        JSON_UNESCAPED_UNICODE
    );
    exit;
}

// 執行期出錯時回傳可讀訊息，而不是讓 Web Station 顯示一片 HTTP 500
function fatal_as_json() {
    $e = error_get_last();
    if ($e && in_array($e['type'], array(E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR), true)) {
        if (!headers_sent()) {
            http_response_code(500);
            header('Content-Type: application/json; charset=utf-8');
        }
        echo json_encode(
            array('success' => false, 'proxy_error' => 'PHP 執行錯誤：' . $e['message'] .
                '（' . basename($e['file']) . ' 第 ' . $e['line'] . ' 行）'),
            JSON_UNESCAPED_UNICODE
        );
    }
}
register_shutdown_function('fatal_as_json');

$hasCurl = function_exists('curl_init');
$hasFopen = (bool) ini_get('allow_url_fopen');
if (!$hasCurl && !$hasFopen) {
    refuse(500, 'PHP 既沒有 curl 擴充功能，allow_url_fopen 也是關閉的，無法轉發。' .
        '請到 Web Station 的 PHP 設定啟用 curl 擴充功能');
}

$cgi = isset($_GET['_cgi']) ? $_GET['_cgi'] : '';
if ($cgi === '') {
    refuse(400, '缺少 _cgi 參數。正確用法：本檔案網址後面接 ?_cgi=auth.cgi');
}
if (!in_array($cgi, $ALLOWED, true)) {
    refuse(403, '這個端點未開放：' . $cgi);
}

// 其餘查詢參數原樣轉給 DSM（例如上傳用的 _sid）
$query = $_GET;
unset($query['_cgi']);
$target = DSM_BASE . '/webapi/' . $cgi;
if (count($query) > 0) {
    $target .= '?' . http_build_query($query);
}

$isPost = (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'POST');

/* ---------- 組出要送給 DSM 的內容 ---------- */
$postBody = null;      // 原始位元組
$postType = null;      // 對應的 Content-Type
$curlFields = null;    // curl 專用（可直接餵檔案）

if ($isPost) {
    if (count($_FILES) > 0) {
        // 照片上傳。PHP 已把 multipart 拆解過，需依原欄位重新組裝。
        foreach ($_FILES as $f) {
            $err = isset($f['error']) ? $f['error'] : UPLOAD_ERR_NO_FILE;
            if ($err !== UPLOAD_ERR_OK) {
                $hint = ($err === UPLOAD_ERR_INI_SIZE || $err === UPLOAD_ERR_FORM_SIZE)
                    ? '照片超過 PHP 的上傳大小上限，請在 Web Station 的 PHP 設定調高 upload_max_filesize 與 post_max_size'
                    : '錯誤碼 ' . $err;
                refuse(400, '檔案上傳失敗：' . $hint);
            }
        }
        if ($hasCurl) {
            $curlFields = $_POST;
            foreach ($_FILES as $name => $f) {
                $type = $f['type'] !== '' ? $f['type'] : 'application/octet-stream';
                $curlFields[$name] = class_exists('CURLFile')
                    ? new CURLFile($f['tmp_name'], $type, $f['name'])
                    : '@' . $f['tmp_name'] . ';type=' . $type . ';filename=' . $f['name'];
            }
        } else {
            $boundary = '----pvshoot' . bin2hex(random_bytes(12));
            $body = '';
            foreach ($_POST as $k => $v) {
                $body .= '--' . $boundary . "\r\n";
                $body .= 'Content-Disposition: form-data; name="' . $k . '"' . "\r\n\r\n";
                $body .= $v . "\r\n";
            }
            foreach ($_FILES as $name => $f) {
                $type = $f['type'] !== '' ? $f['type'] : 'application/octet-stream';
                $body .= '--' . $boundary . "\r\n";
                $body .= 'Content-Disposition: form-data; name="' . $name .
                         '"; filename="' . $f['name'] . '"' . "\r\n";
                $body .= 'Content-Type: ' . $type . "\r\n\r\n";
                $body .= file_get_contents($f['tmp_name']) . "\r\n";
            }
            $body .= '--' . $boundary . "--\r\n";
            $postBody = $body;
            $postType = 'multipart/form-data; boundary=' . $boundary;
        }
    } else {
        // 登入、登出等表單編碼的請求，原樣轉送
        $raw = file_get_contents('php://input');
        if ($raw === false) $raw = '';
        if ($raw === '' && count($_POST) > 0) $raw = http_build_query($_POST);
        $postBody = $raw;
        $postType = isset($_SERVER['CONTENT_TYPE']) && $_SERVER['CONTENT_TYPE'] !== ''
            ? $_SERVER['CONTENT_TYPE']
            : 'application/x-www-form-urlencoded';
        if ($hasCurl) $curlFields = $raw;
    }
}

/* ---------- 送出 ---------- */
$result = false;
$status = 200;
$errText = '';

if ($hasCurl) {
    $ch = curl_init($target);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, false);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
    curl_setopt($ch, CURLOPT_TIMEOUT, 600);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
    if ($isPost) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $curlFields);
        if (is_string($curlFields) && $postType !== null) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: ' . $postType));
        }
    }
    $result = curl_exec($ch);
    if ($result === false) $errText = curl_error($ch);
    else $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);
} else {
    $opts = array('http' => array(
        'method'        => $isPost ? 'POST' : 'GET',
        'timeout'       => 600,
        'ignore_errors' => true,
    ));
    if ($isPost) {
        $opts['http']['header']  = 'Content-Type: ' . $postType . "\r\n" .
                                   'Content-Length: ' . strlen($postBody);
        $opts['http']['content'] = $postBody;
    }
    $result = @file_get_contents($target, false, stream_context_create($opts));
    if ($result === false) {
        $errText = 'file_get_contents 無法連線';
    } elseif (isset($http_response_header[0]) &&
              preg_match('#\s(\d{3})\s#', $http_response_header[0], $m)) {
        $status = (int) $m[1];
    }
}

if ($result === false) {
    refuse(502, '轉發到 DSM 失敗：' . $errText .
        '（確認 DSM 的 HTTP 連接埠是 5000；若已改過，請修改本檔案開頭的 DSM_BASE）');
}

http_response_code($status);
header('Content-Type: application/json; charset=utf-8');
echo $result;
