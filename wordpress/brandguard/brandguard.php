<?php
/**
 * Plugin Name: BrandGuard Review
 * Description: Submit block editor drafts and see the decision for the current draft.
 * Version: 1.0.0
 * Requires at least: 6.6
 * Requires PHP: 7.4
 */
defined( 'ABSPATH' ) || exit;

add_action( 'enqueue_block_editor_assets', function () {
    $screen = get_current_screen();
    if ( ! $screen || 'post' !== $screen->base ) {
        return;
    }
    wp_enqueue_script( 'brandguard-editor', plugins_url( 'editor.js', __FILE__ ),
        array( 'wp-api-fetch', 'wp-components', 'wp-data', 'wp-editor', 'wp-element', 'wp-plugins' ), '1.0.0', true );
} );

function brandguard_post_permission( $request ) {
    $post_id = absint( $request['id'] );
    return get_post( $post_id ) && current_user_can( 'edit_post', $post_id );
}

function brandguard_request( $request ) {
    if ( ! defined( 'BRANDGUARD_URL' ) || ! defined( 'BRANDGUARD_KEY' ) ) {
        return new WP_Error( 'brandguard_config', 'Ask your administrator to configure the BrandGuard URL and connection key.', array( 'status' => 503 ) );
    }
    $origin = untrailingslashit( BRANDGUARD_URL );
    $local = 'local' === wp_get_environment_type() && in_array( wp_parse_url( $origin, PHP_URL_HOST ), array( 'localhost', '127.0.0.1' ), true );
    if ( 'https' !== wp_parse_url( $origin, PHP_URL_SCHEME ) && ! $local ) {
        return new WP_Error( 'brandguard_url', 'Configure an HTTPS BrandGuard URL.', array( 'status' => 503 ) );
    }
    $url = $origin . '/api/wordpress/posts/' . absint( $request['id'] );
    $args = array(
        'method' => $request->get_method(),
        'headers' => array( 'Authorization' => 'Bearer ' . BRANDGUARD_KEY, 'Content-Type' => 'application/json' ),
        'timeout' => 20, 'redirection' => 0, 'limit_response_size' => 16384,
    );
    if ( 'POST' === $args['method'] ) {
        $params = $request->get_json_params();
        if ( ! is_array( $params ) || ! isset( $params['snapshot'] ) || ! is_array( $params['snapshot'] ) ) {
            return new WP_Error( 'brandguard_draft', 'A draft snapshot is required.', array( 'status' => 400 ) );
        }
        $args['body'] = wp_json_encode( array( 'snapshot' => $params['snapshot'],
            'campaign' => defined( 'BRANDGUARD_CAMPAIGN' ) ? BRANDGUARD_CAMPAIGN : 'Unassigned' ) );
    } else {
        $digest = $request->get_param( 'digest' );
        if ( ! is_string( $digest ) || ! preg_match( '/^[a-f0-9]{64}$/D', $digest ) ) {
            return new WP_Error( 'brandguard_digest', 'Invalid draft fingerprint.', array( 'status' => 400 ) );
        }
        $url = add_query_arg( 'digest', $digest, $url );
    }
    $response = wp_remote_request( $url, $args );
    if ( is_wp_error( $response ) ) {
        return new WP_Error( 'brandguard_unavailable', 'Unable to reach BrandGuard. Retry the review check.', array( 'status' => 503 ) );
    }
    $code = wp_remote_retrieve_response_code( $response );
    $result = json_decode( wp_remote_retrieve_body( $response ), true );
    if ( 200 !== $code || ! is_array( $result ) || ! isset( $result['status'], $result['digest'] ) ) {
        $message = isset( $result['detail'] ) && is_string( $result['detail'] ) ? $result['detail'] : 'BrandGuard could not verify this draft. Check its size and the connection settings.';
        return new WP_Error( 'brandguard_review', $message, array( 'status' => $code >= 400 && $code <= 599 ? $code : 502 ) );
    }
    if ( isset( $result['submission_id'] ) && wp_is_uuid( $result['submission_id'], 4 ) ) {
        $result['review_url'] = $origin . '/#review/' . $result['submission_id'];
    }
    $reply = rest_ensure_response( $result );
    $reply->header( 'Cache-Control', 'private, no-store' );
    return $reply;
}

add_action( 'rest_api_init', function () {
    register_rest_route( 'brandguard/v1', '/posts/(?P<id>[1-9]\d*)', array(
        'methods' => array( 'GET', 'POST' ),
        'callback' => 'brandguard_request',
        'permission_callback' => 'brandguard_post_permission',
    ) );
} );
