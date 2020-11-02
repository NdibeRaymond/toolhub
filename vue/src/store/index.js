import Vue from 'vue';
import Vuex from 'vuex';
import SwaggerClient from 'swagger-client';

Vue.use( Vuex );

export default new Vuex.Store( {
	state: {
		user: {
			is_authenticated: false,
			csrf_token: ''
		},
		userCreatedUrls: [],
		apiErrorMsg: ''
	},
	mutations: {
		USER( state, user ) {
			state.user = user;
		},
		USER_CREATED_URLS( state, urls ) {
			state.userCreatedUrls = urls;
			state.apiErrorMsg = '';
		},
		REGISTER_URL( state, urlObj ) {
			state.userCreatedUrls.push( urlObj );
			state.apiErrorMsg = '';
		},
		UNREGISTER_URL( state, url ) {
			const index = state.userCreatedUrls.findIndex( ( obj ) => obj.url === url );
			state.userCreatedUrls.splice( index, 1 );
			state.apiErrorMsg = '';
		},
		ERROR( state, error ) {
			state.apiErrorMsg = error;
		}
	},
	actions: {
		getUserInfo( context ) {
			fetch( '/api/user/', { credentials: 'same-origin' } )
				.then( ( response ) => response.json() )
				.then( ( data ) => ( context.commit( 'USER', data ) ) );
		},
		registerUrl( context, url ) {
			if ( !this.state.user.is_authenticated ) {
				return;
			}

			const request = {
				url: '/api/crawler/urls/',
				method: 'POST',
				body: '{ "url": "' + url + '" }',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFTOKEN': this.state.user.csrf_token
				}
			};

			SwaggerClient.http( request ).then( ( response ) => {
				context.commit( 'REGISTER_URL', JSON.parse( response.text ) );
			} )
				.catch( ( err ) => context.commit( 'ERROR', err ) );
		},
		unregisterUrl( context, urlObj ) {
			if ( !this.state.user.is_authenticated ) {
				return;
			}

			const request = {
				url: '/api/crawler/urls/' + urlObj.id + '/',
				method: 'DELETE',
				headers: {
					'X-CSRFTOKEN': this.state.user.csrf_token
				}
			};

			SwaggerClient.http( request ).then( () => {
				context.commit( 'UNREGISTER_URL', urlObj.url );
			} )
				.catch( ( err ) => context.commit( 'ERROR', err ) );
		},
		getUrlsCreatedByUser( context ) {
			if ( !this.state.user.is_authenticated ) {
				return;
			}

			const request = {
				url: '/api/crawler/urls/self/',
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				}
			};

			SwaggerClient.http( request ).then( ( response ) => {
				context.commit( 'USER_CREATED_URLS', response.body.results );
			} )
				.catch( ( err ) => context.commit( 'ERROR', err ) );
		}
	},
	modules: {
	},
	// Strict mode in development/testing, but disabled for performance in prod
	strict: process.env.NODE_ENV !== 'production'
} );
