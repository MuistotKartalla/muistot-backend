FROM node:current-alpine
RUN npm install -g maildev
CMD maildev
