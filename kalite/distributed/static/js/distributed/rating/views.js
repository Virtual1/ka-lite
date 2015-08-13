var Backbone = require("../base/backbone");
var $ = require("../base/jQuery");
var _ = require("underscore");
var BaseView = require("../base/baseview");
var Handlebars = require("../base/handlebars");

/*
    Container view for feedback form.
    See the design document here: https://docs.google.com/a/learningequality.org/document/d/1W_2vv1cZU5wZp_MLjvPy6jHwkRVPW_iTJhHEpSOYrCs/edit?usp=drive_web
*/
module.exports = BaseView.extend({

    template: require("./hbtemplates/rating.handlebars"),

    events: {
        "click .rating-submit": "submit_rating",
        "click .rating-edit": "edit_callback",
        "click .rating-delete": "delete_callback"
    },

    initialize: function(options) {
        /*
            Prepare self and subviews.
        */
        this.model = options.model || function() {
            var model = new Backbone.Model();
            model.url = "/api/not/gonna/work";
            return model;
        }();
        _.bindAll(this, "delete_callback", "submit_rating", "edit_callback", "render1st", "render2nd", "render3rd", "renderTextArea", "renderAll", "render");
    },

    render: function() {
        if( this.model.isNew() || this.model.get("rating1") === 0) {
            this.render1st();
        } else {
            this.renderAll();
        }
    },

    add_subview_and_once: function(view_class, name, options, event, callback) {
        /*
            Repeated logic for displaying each subwidget once, then removing it after user has interacted with it
            and displaying the next widget in the sequence.
        */
        this[name] = this.add_subview(view_class, options);
        var self = this;
        this.model.once(event, function() {
            self[name].remove();
            callback();
        });
    },

    render1st: function() {
        /*
            Render the first star rating, then wait until it's been rated to show the next step.
            Called when the view's model is not fetched successfully -- particularly when it doesn't yet exist.
        */
        this.$el.html(this.template());
        this.$(".rating-submit").hide();
        this.$(".rating-edit").hide();
        this.$(".rating-skip").hide();
        this.$(".rating-delete").hide();
        this.add_subview_and_once(StarView, "star_view_1",
            {el: this.$("#star-container-1"), model: this.model, rating_attr: "rating1"},
            "change:rating1", this.render2nd);
    },

    render2nd: function() {
        this.add_subview_and_once(StarView, "star_view_2",
            {el: this.$("#star-container-2"), model: this.model, rating_attr: "rating2"},
            "change:rating2", this.render3rd);
    },

    render3rd: function() {
        this.add_subview_and_once(StarView, "star_view_3",
            {el: this.$("#star-container-3"), model: this.model, rating_attr: "rating3"},
            "change:rating3", this.renderTextArea);
    },

    renderTextArea: function() {
        this.$(".rating-submit").show();
        this.$(".rating-skip").show();
        this.text_view = this.add_subview(TextView, {
            el: this.$("#text-container"),
            model: this.model
        });
        var self = this;
        // Wrap in _.once, since it could potentially be called twice by different callbacks
        var callback = _.once(function() {
            self.text_view.remove();
            self.renderAll();
        });
        this.$(".rating-submit").one("click", function() {
            // Update the model explicitly before removing the view, since the callback for changed text is debounced
            self.text_view.model.set(self.text_view.text_attr, self.text_view.$(".rating-text-feedback")[0].value);
            callback();
        });
        this.$(".rating-skip").one("click", function() {
            self.text_view.model.set(self.text_view.text_attr, "");
            callback();
        });
    },

    renderAll: function() {
        /*
            Renders itself, then attaches all subviews.
            Called when: 1) The view's model is fetched successfully or
                         2) The view's model is not fetched, and the user finishes filling out the new form.
        */
        this.$el.html(this.template());
        // Explicitly hide/display desired buttons, since we re-render the template
        this.$(".rating-skip").hide();
        this.$(".rating-edit").hide();
        var views_and_opts = [
            ["star_view_1", StarView, {el: this.$("#star-container-1"), model: this.model, rating_attr: "rating1"}],
            ["star_view_2", StarView, {el: this.$("#star-container-2"), model: this.model, rating_attr: "rating2"}],
            ["star_view_3", StarView, {el: this.$("#star-container-3"), model: this.model, rating_attr: "rating3"}],
            ["text_view", TextView, {el: this.$("#text-container"), model: this.model, rating_attr: "text"}]
        ];
        var self = this;
        _.each(views_and_opts, function(el, ind, list){
            self[el[0]] = self.add_subview(el[1], el[2]);
        });
        this.submit_rating();
    },

    submit_rating: function() {
        this.text_view.toggle_disabled(true);
        this.$(".rating-submit").hide();
        this.$(".rating-edit").show();
        this.model.save();
    },

    edit_callback: function() {
        this.text_view.toggle_disabled(false);
        this.$(".rating-submit").show();
        this.$(".rating-edit").hide();
    },

    delete_callback: function() {
        var self = this;
        this.$el.html("Deleting your review...");
        // Don't simply clear & destroy the model, we wish to remember some attributes (like content_kind and user_uri)
        this.model.save({
            rating1: 0,
            rating2: 0,
            rating3: 0,
            text: "",
        },
        {
            error: function(){
                console.log("failed to clear rating model attributes...");
            },
            success: function(){
                self.render1st();
            },
            patch: true
        });
    }
});


/*
    Widget to rate something from 1 to 5 stars.
*/
var StarView = BaseView.extend({

    template: require("./hbtemplates/star.handlebars"),

    events: {
        "click .star-rating-option": "rate_value_callback"
    },

    initialize: function(options) {
        this.model = options.model || new Backbone.Model();
        this.rating_attr = options.rating_attr || "rating";
        _.bindAll(this, "rate_value_callback", "rating_change");

        this.model.on("change:"+this.rating_attr, this.rating_change);

        this.render();
    },

    render: function() {
        this.$el.html(this.template(this.model.attributes));
        this.rating_change();
    },

    rate_value_callback: function(ev) {
        var val = $(ev.target).attr("data-val");
        this.model.set(this.rating_attr, val);
    },

    rating_change: function() {
        opts = this.$(".star-rating-option");
        _.each(opts, function(opt, index, list) {
            $opt = $(opt);
            $opt.toggleClass("activated", parseInt($opt.attr("data-val")) <= parseInt(this.model.get(this.rating_attr)));
        }, this);
    }
});


/*
    Widget to accept/display free-form text input.
*/
var TextView = BaseView.extend({

    template: require("./hbtemplates/text.handlebars"),

    events: {
        "keyup .rating-text-feedback": "text_changed"
    },

    initialize: function(options) {
        this.model = options.model || new Backbone.Model();
        this.text_attr = options.text_attr || "text";
        _.bindAll(this, "toggle_disabled", "is_disabled", "text_changed");
        this.model.on("change:"+this.text_attr, this.text_changed);
        this.render();
    },

    render: function() {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },

    /* Debounce'd -- waits until the input stops arriving (500 ms) to update the model */
    text_changed: _.debounce(function() {
        this.model.set(this.text_attr, this.$(".rating-text-feedback")[0].value);
    }, 500),

    toggle_disabled: function(val) {
        if( typeof val === "undefined" ) {
            val = !this.is_disabled();
        }
        this.$(".rating-text-feedback").attr("disabled", val);
        return this;
    },

    is_disabled: function() {
        return this.$(".rating-text-feedback").attr("disabled") === "disabled";
    }
});