import Vue from 'vue';
import Vuex from 'vuex';
import { makeApiCall, getFailurePayload } from '@/plugins/swagger';
import i18n from '@/plugins/i18n';
import { asApp, asToken } from '@/helpers/casl';

Vue.use( Vuex );

export const actions = {
	registerApp( context, app ) {
		const request = {
			url: '/api/oauth/applications/',
			method: 'POST',
			body: JSON.stringify( app )
		};

		return makeApiCall( context, request ).then(
			( success ) => {
				context.commit( 'REGISTER_APP', success.body );

				this._vm.$notify.success(
					i18n.t( 'developersettings-appregistersuccesstext', [ success.body.name ] )
				);
			},
			( failure ) => {
				const data = getFailurePayload( failure );
				context.commit( 'REGISTER_APP', false );

				for ( const err in data.errors ) {
					this._vm.$notify.error(
						i18n.t( 'apierrors', [
							data.errors[ err ].field,
							data.errors[ err ].message
						] )
					);
				}
			}
		);
	},
	listClientApps( context, page ) {
		const request = {
			url: '/api/oauth/applications/?page=' + page,
			method: 'GET'
		};

		return makeApiCall( context, request ).then(
			( success ) => {
				context.commit( 'CLIENT_APPS', success.body );
			},
			( failure ) => {
				const explanation = ( 'statusCode' in failure ) ?
					failure.response.statusText : failure;

				this._vm.$notify.error(
					i18n.t( 'apierror', [ explanation ] )
				);
			}
		);
	},
	updateClientApp( context, app ) {
		const request = {
			url: '/api/oauth/applications/' + app.clientId + '/',
			method: 'PATCH',
			body: JSON.stringify( { redirect_url: app.redirectUrl } )
		};

		return makeApiCall( context, request ).then(
			() => {
				this._vm.$notify.success(
					i18n.t( 'developersettings-appupdatesuccess', [ app.clientId ] )
				);
			},
			() => {
				this._vm.$notify.error(
					i18n.t( 'developersettings-appupdateerror', [ app.clientId ] )
				);
			}
		);
	},
	deleteClientApp( context, clientId ) {
		const request = {
			url: '/api/oauth/applications/' + clientId + '/',
			method: 'DELETE'
		};

		return makeApiCall( context, request ).then(
			() => {
				context.commit( 'DELETE_CLIENT_APP', clientId );

				this._vm.$notify.error(
					i18n.t( 'appdeleted', [ clientId ] )
				);
			},
			( failure ) => {
				const explanation = ( 'statusCode' in failure ) ?
					failure.response.statusText : failure;

				this._vm.$notify.error(
					i18n.t( 'apierror', [ explanation ] )
				);
			}
		);
	},
	listAuthorizedApps( context, page ) {
		const request = {
			url: '/api/oauth/authorized/?page=' + page,
			method: 'GET'
		};

		return makeApiCall( context, request ).then(
			( success ) => {
				context.commit( 'AUTHORIZED_APPS', success.body );
			},
			( failure ) => {
				const explanation = ( 'statusCode' in failure ) ?
					JSON.parse( failure.response.data ) :
					failure;

				this._vm.$notify.error(
					i18n.t( 'apierror', [ explanation ] )
				);
			}
		);
	},
	deleteAuthorizedApp( context, id ) {
		const request = {
			url: '/api/oauth/authorized/' + id + '/',
			method: 'DELETE'
		};

		return makeApiCall( context, request ).then(
			() => {
				context.commit( 'DELETE_AUTHORIZED_APP', id );

				this._vm.$notify.error(
					i18n.t( 'appdeleted', [ id ] )
				);
			},
			( failure ) => {
				const explanation = ( 'statusCode' in failure ) ?
					JSON.parse( failure.response.data ) :
					failure;

				this._vm.$notify.error(
					i18n.t( 'apierror', [ explanation ] )
				);
			}
		);
	}
};

export const mutations = {
	REGISTER_APP( state, app ) {
		if ( app ) {
			const application = asApp( app );
			state.clientAppCreated = application;
			state.clientApps.push( application );
			state.numClientApps += 1;
		} else {
			state.clientAppCreated = app;
		}
	},
	CLIENT_APPS( state, apps ) {
		state.clientApps = asApp( apps.results );
		state.numClientApps = apps.count;
	},
	DELETE_CLIENT_APP( state, clientId ) {
		const index = state.clientApps.findIndex(
			( obj ) => obj.client_id === clientId
		);
		state.clientApps.splice( index, 1 );
		state.numClientApps -= 1;
	},
	AUTHORIZED_APPS( state, apps ) {
		state.authorizedApps = asToken( apps.results );
		state.numAuthorizedApps = apps.count;
	},
	DELETE_AUTHORIZED_APP( state, id ) {
		const index = state.authorizedApps.findIndex(
			( obj ) => obj.id === id
		);
		state.authorizedApps.splice( index, 1 );
		state.numAuthorizedApps -= 1;
	}
};

export default {
	namespaced: true,
	state: {
		clientApps: [],
		numClientApps: 0,
		authorizedApps: [],
		numAuthorizedApps: 0,
		clientAppCreated: {}
	},
	actions: actions,
	mutations: mutations,
	// Strict mode in development/testing, but disabled for performance in prod
	strict: process.env.NODE_ENV !== 'production'
};
