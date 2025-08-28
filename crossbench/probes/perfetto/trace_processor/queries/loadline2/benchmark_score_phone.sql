INCLUDE PERFETTO MODULE ext.loadline2_amazon_product;
INCLUDE PERFETTO MODULE ext.loadline2_cnn_article;
INCLUDE PERFETTO MODULE ext.loadline2_globo_homepage;
INCLUDE PERFETTO MODULE ext.loadline2_google_search_result;
INCLUDE PERFETTO MODULE ext.loadline2_wikipedia_article;

SELECT
  loadline2_amazon_product_score_visual() AS amazon_product_visual,
  loadline2_amazon_product_score_interactive() AS amazon_product_interactive,
  loadline2_cnn_article_score_visual() AS cnn_article_visual,
  loadline2_cnn_article_score_interactive() AS cnn_article_interactive,
  loadline2_wikipedia_article_score_visual() AS wikipedia_article_visual,
  loadline2_wikipedia_article_score_interactive() AS wikipedia_article_interactive,
  loadline2_globo_homepage_score_visual() AS globo_homepage_visual,
  loadline2_globo_homepage_score_interactive() AS globo_homepage_interactive,
  loadline2_google_search_result_score_visual() AS google_search_result_visual,
  loadline2_google_search_result_score_interactive() AS google_search_result_interactive;
