<?php
// 環境檢查：故意只用最基本的語法，任何 PHP 版本都跑得起來。
// 用來確認 proxy.php 需要的功能是否齊備。放在 proxy.php 旁邊，開啟後看結果。
header('Content-Type: application/json; charset=utf-8');

$info = array(
    'php_version'      => PHP_VERSION,
    'has_curl'         => function_exists('curl_init'),
    'has_json'         => function_exists('json_encode'),
    'allow_url_fopen'  => ini_get('allow_url_fopen') ? true : false,
    'upload_max'       => ini_get('upload_max_filesize'),
    'post_max'         => ini_get('post_max_size'),
    'display_errors'   => ini_get('display_errors') ? true : false,
    'loaded_extensions'=> implode(',', get_loaded_extensions()),
);

// 能不能連到 DSM
$info['dsm_reachable'] = false;
$info['dsm_note'] = '';
if (function_exists('curl_init')) {
    $ch = curl_init('http://localhost:5000/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 8);
    $r = curl_exec($ch);
    if ($r === false) {
        $info['dsm_note'] = 'curl 連線失敗：' . curl_error($ch);
    } else {
        $info['dsm_reachable'] = (strpos($r, 'SYNO.API') !== false);
        $info['dsm_note'] = '收到 ' . strlen($r) . ' 位元組';
    }
    curl_close($ch);
} elseif (ini_get('allow_url_fopen')) {
    $r = @file_get_contents('http://localhost:5000/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query');
    if ($r === false) {
        $info['dsm_note'] = 'file_get_contents 連線失敗';
    } else {
        $info['dsm_reachable'] = (strpos($r, 'SYNO.API') !== false);
        $info['dsm_note'] = '收到 ' . strlen($r) . ' 位元組（用 file_get_contents）';
    }
} else {
    $info['dsm_note'] = 'curl 與 allow_url_fopen 都不可用，無法對外連線';
}

echo json_encode($info, 128 | 256); // JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES
