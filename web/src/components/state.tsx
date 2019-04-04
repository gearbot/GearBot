export interface GearState {
	rotation: number;
	spinning: boolean;
}

export interface DashboardState {
	currentUrl: string;
	validSession: boolean;
}

export interface HeaderState {}

export interface GuildPageState {
	guildPageStats: GuildPageStats
}

export interface GuildListNavState {
	guilds: GuildListObject[];
	guildsLoaded: boolean;
}

export interface GuildListObject {
	name: string;
	icon: string;
	authorized: boolean;
}

export interface GuildPageStats {
	name: string;
	owner: string;
	id: number;
	memberCount: number;
	textChannels: number;
	voiceChannels: number;
	totalChannels: number;
	creationDate: string; // This will be a server-side formatted string
	vipFeatures: boolean; // Add actual parts later, for now just a does have or doesn't check
	serverIcon: string;
	roles: []
	serverEmoteCount: number;
	memberStatuses: {
		online: number
		idle: number;
		dnd: number;
		offline: number;
	} 
}

export interface DocState {
	markdown: string;
	link: string;
}

export interface AntiraidState {
	blockCount: number;
	blockStates: AntiraidBlock[]
}

export interface BotStats {
	uptimeCount: string;
	commandCount: number;
	messageCount: number;
	guildCount: number;
	errorCount: number;
	userCount: number;
	uniqueUserCount: number;
	tacoTime: number;
}

export interface BotInfoPageState extends BotStats {
	initalLoadDone: boolean;
	socketConnected: boolean; // Look into adding this to all socket using pages
}

export interface DashboardState {
	currentComponent: JSX.Element;
}

export interface AuthObject {
	client_id: string;
	timestamp: string;
	client_token?: string;
	errorValue?: number;
	user_auth_token?: string // This is for the Discord OAuth verification or whatnot
}

export interface InitalAuthObject extends AuthObject {
	status: number;
}

export interface AntiraidBlock {
	name: string;
	displayText: string;
	description: string;
	isBeingDragged: boolean;
	position: {x: number, y: number};
}
